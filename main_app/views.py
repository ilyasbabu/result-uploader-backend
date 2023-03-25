"""
Views Naming Convention : [Functionality]View[User-Role-Accessible(optional)]
"""
import time
from django.shortcuts import render
from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from rest_framework import status

from .authentication import CustomTokenAuthentication
from .serializers import (
    UserLoginSerializer,
    StudentCreateSerializer,
    StudentListSerialzer,
    MarksViewRequestSerialzerFaculty,
    MarksViewRequestSerialzerStudent,
    MarksViewSerializer,
)
from .models import User, UserAuthToken, Subject, Exam, Course, Student, Faculty, Mark, MarkSheetDoc, ROLE_CHOICES
from .services import (
    verify_document,
    validate_file_upload_request,
    verify_file_type,
    retreive_and_save_marks,
    validate_login_data,
    get_login_user,
    create_auth_token,
    login_success_data,
    handle_error
)


# Create your views here.



class LoginView(APIView):

    authentication_classes = [CustomTokenAuthentication]

    def post(self, request):
        try:
            username, password = validate_login_data(request.data)
            user = get_login_user(username, password)
            token = create_auth_token(user)
            data = login_success_data(user, token)
            return Response(status=status.HTTP_201_CREATED, data=data)
        except Exception as e:
            msg = handle_error(e)
            return Response(status=status.HTTP_404_NOT_FOUND, data=msg)


class LoginDataView(APIView):
    """Login data view from token"""

    authentication_classes = [CustomTokenAuthentication]

    def get(self, request):
        user = request.user
        res = {}
        res["username"] = user.username
        res["user_role"] = user.role
        res['role_name'] = dict(ROLE_CHOICES).get(user.role)
        if user.role == 2:
            faculty = Faculty.objects.get(user=user)
            course = faculty.course.course_name
        elif user.role == 3:
            student = Student.objects.get(user=user)
            course = student.course.course_name
        res['course'] = course
        return Response(status=status.HTTP_200_OK, data=res)


class StudentCreateViewFaculty(APIView):
    """Student creation API for faculty"""

    authentication_classes = [CustomTokenAuthentication]

    def post(self, request):
        try:
            # check permision
            user = request.user
            has_permission = User.objects.filter(id=user.id, role__in=[1,2]).exists()
            if not has_permission:
                raise ValidationError("You do not have permission to create Student.")

            # validating data
            serializer = StudentCreateSerializer(data=request.data)
            serializer.is_valid()
            if serializer.errors:
                error_list = [
                    f"{error.upper()}: {serializer.errors[error][0]}"
                    for error in serializer.errors
                ]
                raise ValidationError(error_list)

            #retreving data
            username = serializer.validated_data.get("username")
            username_exists = User.objects.filter(username=username).exists()
            if username_exists:
                raise ValidationError("Username already exists")
            name = serializer.validated_data.get("name")
            registration_no = serializer.validated_data.get("registration_no")

            faculty = Faculty.objects.get(user=user)
            course = faculty.course

            # create user for student
            with transaction.atomic():
                st_user = User.objects.create_user(username=username, password='12345', role=3)
                st_user.first_name = name
                st_user.full_clean()
                st_user.save()

                student = Student(
                    user = st_user,
                    registration_no = registration_no,
                    course = course,
                    added_by = user,
                )
                student.save()

            return Response(status=status.HTTP_201_CREATED, data='Student created successfully')
        except Exception as e:
            msg = handle_error(e)
            return Response(status=status.HTTP_404_NOT_FOUND, data=msg)


class ExamDropdownViewStudent(APIView):

    authentication_classes = [CustomTokenAuthentication]

    def get(self, request):
        exams = Exam.objects.filter(is_active = True).values("id", "exam_name")
        return Response(status=status.HTTP_200_OK, data=exams)


class SubjectDropdownViewStudent(APIView):
    """Subject Dropdown For Selected Exam"""

    authentication_classes = [CustomTokenAuthentication]

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # retrieving user information from the request and checking if it is student
        user = request.user
        if user.role != 3:
            return Response(status=status.HTTP_400_BAD_REQUEST, data="Log in as student to get subjects")

        # retrieving student object fropm database and getting related course object
        student = Student.objects.filter(user=user, is_active=True)[0]
        student_course = student.course
        
        # retreiving exam id from request and returns error msg if not provided
        exam_id = request.GET.get("exam")
        if exam_id in [None, 'undefined', '']:
            return Response(status=status.HTTP_400_BAD_REQUEST, data="Provide Exam id along with the request")

        # retrieving data from database with students course and exam id provided
        subjects = Subject.objects.filter(course=student_course, exam_id=exam_id).values("id", "subject_name")
        return Response(status=status.HTTP_200_OK, data=subjects)


class StudentDropdownViewFaculty(APIView):
    """Student List view for faculty"""

    authentication_classes = [CustomTokenAuthentication]

    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            if user.role != 2:
                raise ValidationError("You must be logged in as Faculty to view Students")
            
            faculty = Faculty.objects.filter(user=user, is_active=True)[0]
            faculty_course = faculty.course

            students = Student.objects.filter(is_active=True, course=faculty_course)
            serializer = StudentListSerialzer(students, many=True)

            return Response(status=status.HTTP_200_OK, data=serializer.data)
        except Exception as e:
            msg = handle_error(e)
            return Response(status=status.HTTP_404_NOT_FOUND, data=msg)


class MarkSheetFileUploadViewStudent(APIView):
    """API for uploading mark sheet file to students"""

    authentication_classes = [CustomTokenAuthentication]

    def post(self, request):
        try:
            # user verification
            time.sleep(1)
            user = request.user
            student = Student.objects.filter(user=user, is_active=True)
            if not student.exists():
                raise ValidationError("You must be logged in as Student to perform this action")
            student = student[0]

            # retreiving data from request
            file = request.FILES.get('doc')
            exam_id = request.POST.get('exam')
            validate_file_upload_request(exam_id, file)

            exam = Exam.objects.get(id=exam_id)

            already_uploaded = Mark.objects.filter(student=student, exam=exam).exists()
            if already_uploaded:
                raise ValidationError("You have already uploaded marks for this exam")

            verify_file_type(file)
            retreive_and_save_marks(user, file, exam, student)
            return Response(status=status.HTTP_200_OK, data="Mark Sheet Uploaded Succesfully!")
        except Exception as e:
            msg = handle_error(e)
            return Response(status=status.HTTP_404_NOT_FOUND, data=msg)
        

class ViewMarkSheetView(APIView):
    """View Mark Sheet Uploaded by the Student"""

    authentication_classes = [CustomTokenAuthentication]

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            role = user.role

            if role == 2: # faculty
                serializer = MarksViewRequestSerialzerFaculty(data=request.GET)
                serializer.is_valid()
                if serializer.errors:
                    error_list = [
                        f"{error.upper()}: {serializer.errors[error][0]}"
                        for error in serializer.errors
                    ]
                    raise ValidationError(error_list)
                student_id = serializer.validated_data.get("student")
                student = Student.objects.get(id=student_id)

            elif role == 3: # student
                serializer = MarksViewRequestSerialzerStudent(data=request.GET)
                serializer.is_valid()
                if serializer.errors:
                    error_list = [
                        f"{error.upper()}: {serializer.errors[error][0]}"
                        for error in serializer.errors
                    ]
                    raise ValidationError(error_list)
                student = Student.objects.get(user=user)

            exam_id = serializer.validated_data.get("exam")
            exam = Exam.objects.get(id=exam_id)

            marks = Mark.objects.filter(student=student, exam=exam, is_active=True)
            serializer = MarksViewSerializer(marks, many=True)
            res = {}
            mark_sheet = MarkSheetDoc.objects.filter(student=student,exam=exam, is_active=True)
            if mark_sheet.exists():
                mark_sheet = mark_sheet[0]
                res["marksheet_id"] = mark_sheet.id
                res["status"] = mark_sheet.status
                res["sgpa"] = mark_sheet.sgpa
            else:
                res["marksheet_id"] = ""
                res["status"] = ""
                res["sgpa"] = ""

            res["student"] = student.user.first_name
            res["course"] = student.course.course_name
            res["exam"] = exam.exam_name
            res["mark_list"] = serializer.data
            return Response(status=status.HTTP_200_OK, data=res)
        except Exception as e:
            msg = handle_error(e)
            return Response(status=status.HTTP_404_NOT_FOUND, data=msg)


class ApproveMarklistView(APIView):
    """API for approve/reject MarkSheet for faculty"""

    authentication_classes = [CustomTokenAuthentication]

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            role = user.roles
            if role != 2:
                return Response(status=status.HTTP_200_OK, data="No permission to approve/reject MarkSheet")
            marksheet_id = request.POST.get("marksheet")
            marksheet = MarkSheetDoc.objects.get(id=marksheet_id)
            status = request.POST.get("status")
            if status == "Approve":
                marksheet.status = "Approved"
                marksheet.full_clean()
                marksheet.save()
                return Response(status=status.HTTP_200_OK, data="Approved Successfully!!")
            elif status == "Reject":
                marksheet.status = "Rejected"
                marksheet.full_clean()
                marksheet.save()
                return Response(status=status.HTTP_200_OK, data="Rejected Successfully!!")
            return Response(status=status.HTTP_200_OK, data="Something went wrong!!")
        except Exception as e:
            msg = handle_error(e)
            return Response(status=status.HTTP_404_NOT_FOUND, data=msg)


class StudentDetailView(APIView):

    authentication_classes = [CustomTokenAuthentication]

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        student_id = request.GET.get("student")
        student = Student.objects.get(id=student_id)
        res = {}
        res["student"] = student.user.first_name
        res["course"] = student.course.course_name
        return Response(status=status.HTTP_200_OK, data=res)


class ListStudentsView(APIView):
    pass