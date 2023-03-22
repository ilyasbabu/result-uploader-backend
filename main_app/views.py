"""
Views Naming Convention : [Functionality]View[User-Role-Accessible(optional)]
"""
import sys
import string
import random
import traceback
import pdfplumber
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


# Create your views here.



class LoginView(APIView):

    authentication_classes = [CustomTokenAuthentication]

    def post(self, request):
        try:
            # validating data
            serializer = UserLoginSerializer(data=request.data)
            serializer.is_valid()
            if serializer.errors:
                error_list = [
                    f"{error.upper()}: {serializer.errors[error][0]}"
                    for error in serializer.errors
                ]
                raise ValidationError(error_list)
            username = serializer.validated_data.get("username")
            password = serializer.validated_data.get("password")

            # checking user
            try:
                user = User.objects.get(username=username)
                success = user.check_password(password)
                admin = False
                if user.role == 1:
                    admin = True
                if not success:
                    raise User.DoesNotExist
                if admin:
                    raise ValidationError("Admin user!!!")
            except User.DoesNotExist:
                raise ValidationError("Invalid Username or Password")

            # creating token
            string_chars = string.ascii_lowercase + string.digits
            token = "".join(random.choice(string_chars) for _ in range(15))
            while UserAuthToken.objects.filter(key=token).exists():
                token = "".join(random.choice(string_chars) for _ in range(15))
            UserAuthToken.objects.filter(user=user).update(is_expired=True)
            user_auth_token = UserAuthToken(user=user, key=token, added_by=user)
            user_auth_token.save()

            # return data
            res = {}
            res["token"] = token
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
            return Response(status=status.HTTP_201_CREATED, data=res)
        except Exception as e:
            msg = "Something went wrong."
            error_info = "\n".join(traceback.format_exception(*sys.exc_info()))
            print(error_info)
            if isinstance(e, ValidationError):
                error_info = "\n".join(e.messages)
                msg = e.messages
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
            msg = "Something went wrong."
            error_info = "\n".join(traceback.format_exception(*sys.exc_info()))
            print(error_info)
            if isinstance(e, ValidationError):
                error_info = "\n".join(e.messages)
                msg = e.messages
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
            msg = "Something went wrong."
            error_info = "\n".join(traceback.format_exception(*sys.exc_info()))
            print(error_info)
            if isinstance(e, ValidationError):
                error_info = "\n".join(e.messages)
                msg = e.messages
            return Response(status=status.HTTP_404_NOT_FOUND, data=msg)



class MarkSheetFileUploadViewStudent(APIView):
    """API for uploading mark sheet file to students"""

    authentication_classes = [CustomTokenAuthentication]

    def post(self, request):
        try:
            # user verification
            user = request.user
            student = Student.objects.filter(user=user, is_active=True)
            if not student.exists():
                raise ValidationError("You must be logged in as Student to perform this action")
            student = student[0]

            # retreiving data from request
            file = request.FILES.get('doc')
            exam_id = request.POST.get('exam')
            exam = Exam.objects.get(id=exam_id)

            already_uploaded = Mark.objects.filter(student=student, exam=exam).exists()
            if already_uploaded:
                raise ValidationError("You have already uploaded marks for this exam")

            # file verification
            file_name = file.name
            file_extension = file.name.split('.')[-1]
            if file_extension != "pdf":
                raise ValidationError("Invalid file type")
            
            # pdf data retrieval
            with pdfplumber.open(file) as pdf:
                first_page = pdf.pages[0]
                marks_list = first_page.extract_table()
                marks_list_length = len(marks_list)
                if marks_list_length < 3 or marks_list_length > 10:
                    raise ValidationError("Invalid pdf")
                
                # mark list data save
                with transaction.atomic():
                    total_credit_points = 0
                    total_credit = 0
                    failed = False
                    for marks in marks_list[1:]:
                        print(marks)
                        subject_code = marks[0]
                        subject_name = marks[1]
                        grade = marks[2]
                        grade_point = marks[3]
                        credit = marks[4]
                        credit_piont = marks[5]
                        mark_status = marks[6]
                        if mark_status == "Failed":
                            failed = True
                        
                        if credit_piont != "--" or failed:
                            total_credit_points += int(credit_piont)
                            total_credit += int(credit)
                        else:
                            credit_piont = 0
                            credit = 0
                            grade_point = 0

                        subject = Subject.objects.filter(subject_code=subject_code, subject_name=subject_name, is_active=True)
                        if not subject.exists():
                            subject = Subject(
                                subject_code=subject_code,
                                subject_name=subject_name,
                                course=student.course,
                                exam=exam,
                                added_by=user,
                            )
                            subject.full_clean()
                            subject.save()
                        subject = subject[0]

                        mark = Mark(
                            subject=subject,
                            grade=grade,
                            grade_point=grade_point,
                            credit=credit,
                            credit_point=credit_piont,
                            status=mark_status,
                            student=student,
                            exam=exam,
                            added_by=user,
                        )
                        mark.full_clean()
                        mark.save()

                    try:
                        sgpa = round(total_credit_points / total_credit, 2)
                        if failed:
                            sgpa = 0
                    except ZeroDivisionError:
                        sgpa = 0

                    mark_doc = MarkSheetDoc(
                        mark_sheet=file,
                        sgpa=sgpa,
                        student=student,
                        exam=exam,
                        added_by=user,
                    )
                    mark_doc.full_clean()
                    mark_doc.save()

            return Response(status=status.HTTP_200_OK, data="Mark Sheet Uploaded Succesfully!")
        except Exception as e:
            msg = "Something went wrong."
            error_info = "\n".join(traceback.format_exception(*sys.exc_info()))
            print(error_info)
            if isinstance(e, ValidationError):
                error_info = "\n".join(e.messages)
                msg = e.messages
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
            return Response(status=status.HTTP_200_OK, data=serializer.data)
        except Exception as e:
            msg = "Something went wrong."
            error_info = "\n".join(traceback.format_exception(*sys.exc_info()))
            print(error_info)
            if isinstance(e, ValidationError):
                error_info = "\n".join(e.messages)
                msg = e.messages
            return Response(status=status.HTTP_404_NOT_FOUND, data=msg)

