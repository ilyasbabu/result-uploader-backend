import sys
import string
import random
import traceback
from django.shortcuts import render
from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from rest_framework import status

from .authentication import CustomTokenAuthentication
from .serializers import UserLoginSerializer, StudentCreateSerializer
from .models import User, UserAuthToken, Subject, Exam, Course, Student, Faculty


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
                if not success:
                    raise User.DoesNotExist
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
            return Response(status=status.HTTP_201_CREATED, data=res)
        except Exception as e:
            msg = "Something went wrong."
            error_info = "\n".join(traceback.format_exception(*sys.exc_info()))
            print(error_info)
            if isinstance(e, ValidationError):
                error_info = "\n".join(e.messages)
                msg = e.messages
            return Response(status=status.HTTP_404_NOT_FOUND, data=msg)


class StudentCreateView(APIView):

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
            course_id = serializer.validated_data.get("course")
            try:
                course = Course.objects.get(id=course_id)
            except Course.DoesNotExist:
                raise ValidationError("Course does not exist")
            registration_no = serializer.validated_data.get("registration_no")

            # create user for student
            with transaction.atomic():
                st_user = User.objects.create_user(username=username, password='12345', role=3)
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


class ExamDropdownView(APIView):

    authentication_classes = [CustomTokenAuthentication]

    def get(self, request):
        exams = Exam.objects.filter(is_active = True).values("id", "exam_name")
        return Response(status=status.HTTP_200_OK, data=exams)


class SubjectDropdownView(APIView):

    authentication_classes = [CustomTokenAuthentication]

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # retrieving user information from the request and checking if it is student
        user = request.user
        if user.role != 3:
            return Response(status=status.HTTP_400_BAD_REQUEST, data="Log in as student to get subjects")

        # retrieving student object fropm database and getting related course object
        student = Student.objects.filter(user=user, is_active=True)
        student_course = student.course
        
        # retreiving exam id from request and returns error msg if not provided
        exam_id = request.GET.get("exam")
        if exam_id in [None, 'undefined', '']:
            return Response(status=status.HTTP_400_BAD_REQUEST, data="Provide Exam id along with the request")

        # retrieving data from database with students course and exam id provided
        subjects = Subject.objects.filter(course=student_course, exam_id=exam_id).values("id", "subject_name")
        return Response(status=status.HTTP_200_OK, data=subjects)







class StudentDropdowns(APIView):
    def get(self, request):
        user = request.user
        student = Student
        res = {}
        subjects = Subject.objects.filter(is_active=True)


