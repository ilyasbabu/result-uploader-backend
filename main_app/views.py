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
    check_deleted,
    handle_error
)


# Create your views here.



class LoginView(APIView):

    authentication_classes = [CustomTokenAuthentication]

    def post(self, request):
        try:
            username, password = validate_login_data(request.data)
            user = get_login_user(username, password)
            check_deleted(user)
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
            res['profile_id'] = faculty.id
            course = faculty.course.course_name
        elif user.role == 3:
            student = Student.objects.get(user=user)
            res['profile_id'] = student.id
            course = student.course.course_name
        res['course'] = course
        return Response(status=status.HTTP_200_OK, data=res)


class ChangePasswordView(APIView):

    authentication_classes = [CustomTokenAuthentication]

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            password = request.POST.get("password")
            confirm_password = request.POST.get("passwordConfirm")
            if password != confirm_password:
                return Response(status=status.HTTP_404_NOT_FOUND, data=["Both password and confirm password should be same!"])
            user.set_password(password)
            user.save()
            return Response(status=status.HTTP_201_CREATED, data="Password changed successfully")
        except Exception as e:
            msg = handle_error(e)
            return Response(status=status.HTTP_404_NOT_FOUND, data=msg)



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
                st_user = User.objects.create_user(username=username, password=registration_no, role=3)
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
        if user.role != 2:
            return Response(status=status.HTTP_400_BAD_REQUEST, data="Log in as faculty to get subjects")

        # retrieving student object fropm database and getting related course object
        faculty = Faculty.objects.filter(user=user, is_active=True)[0]
        faculty_course = faculty.course

        # retrieving data from database with students course and exam id provided
        res = []
        exams = Exam.objects.filter(is_active = True)
        for exam in exams:
            subject_dict = {}
            subjects = Subject.objects.filter(course=faculty_course, exam=exam).values("id", "subject_name")
            subject_dict["exam"] = exam.exam_name
            subject_dict["subjects"] = subjects
            res.append(subject_dict)
        return Response(status=status.HTTP_200_OK, data=res)


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
                res["marksheet_doc"] = "/media/"+str(mark_sheet.mark_sheet)
                res["status"] = mark_sheet.status
                res["sgpa"] = mark_sheet.sgpa
            else:
                res["marksheet_id"] = ""
                res["marksheet_doc"] = ""
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
            role = user.role
            if role != 2:
                return Response(status=status.HTTP_404_NOT_FOUND, data="No permission to approve/reject MarkSheet")
            print(request.data)
            marksheet_id = request.data.get("marksheet")
            marksheet = MarkSheetDoc.objects.get(id=marksheet_id)
            status_ = request.data.get("status")
            if status_ == "Approve":
                marksheet.status = "Approved"
                marksheet.full_clean()
                marksheet.save()
                return Response(status=status.HTTP_200_OK, data="Approved Successfully!!")
            elif status_ == "Reject":
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


class SubjectWiseResultView(APIView):
    
    authentication_classes = [CustomTokenAuthentication]

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        subject_id = request.GET.get("subject")
        res = {}
        subject = Subject.objects.get(id=subject_id)
        marks = Mark.objects.filter(subject=subject).values(
            "student__user__first_name",
            "grade",
            "grade_point",
            "credit",
            "credit_point",
            "status",
        )
        res["marks"] = marks
        res["subject"] = subject.subject_name

        
        return Response(status=status.HTTP_200_OK, data=res)


class MarkSheetEditView(APIView):

    authentication_classes = [CustomTokenAuthentication]

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        mark_id = request.POST.get("id")
        grade = request.POST.get("grade")
        grade_point = request.POST.get("grade_point")
        credit = request.POST.get("credit")
        credit_point = request.POST.get("credit_point")
        mark = Mark.objects.get(id=mark_id)
        mark.grade = grade
        mark.grade_point = grade_point
        mark.credit = credit
        mark.credit_point = credit_point
        mark.full_clean()
        mark.save()
        return Response(status=status.HTTP_200_OK, data="Updated mark")
    

class ConfirmMarkChangesView(APIView):

    authentication_classes = [CustomTokenAuthentication]

    permission_classes = [IsAuthenticated]

    def post(self, request):
        mark_sheet_id = request.POST.get("id")
        markSheet = MarkSheetDoc.objects.get(id=mark_sheet_id)
        markSheet.status = "Pending"
        markSheet.full_clean()
        markSheet.save()
        return Response(status=status.HTTP_200_OK, data="Updated mark")


class StudentDeleteView(APIView):

    authentication_classes = [CustomTokenAuthentication]

    permission_classes = [IsAuthenticated]

    def post(self, request):
        student_id = request.POST.get("student")
        student = Student.objects.get(id=student_id)
        user = student.user
        with transaction.atomic():
            student.is_active = False
            student.full_clean()
            student.save()
            user.is_active = False
            user.save()

        return Response(status=status.HTTP_200_OK, data="Student deleted Successfully!")


