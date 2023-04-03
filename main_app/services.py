import sys
import string
import random
import traceback
import pdfplumber

from django.db import transaction
from django.core.exceptions import ValidationError
from .serializers import UserLoginSerializer
from .models import (
    User,
    UserAuthToken,
    ROLE_CHOICES,
    Faculty,
    Student,
    Subject, 
    Mark,
    MarkSheetDoc, 
)


def handle_error(e):
    msg = ["Something went wrong."]
    error_info = "\n".join(traceback.format_exception(*sys.exc_info()))
    print(error_info)
    if isinstance(e, ValidationError):
        error_info = "\n".join(e.messages)
        msg = e.messages
    return msg


def validate_login_data(data):
    serializer = UserLoginSerializer(data=data)
    serializer.is_valid()
    if serializer.errors:
        error_list = [
            f"{error.upper()}: {serializer.errors[error][0]}"
            for error in serializer.errors
        ]
        raise ValidationError(error_list)
    username = serializer.validated_data.get("username")
    password = serializer.validated_data.get("password")
    return username, password


def get_login_user(username, password):
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
        return user
    except User.DoesNotExist:
        raise ValidationError("Invalid Username or Password")


def check_deleted(user):
    role = user.role
    if role == 3:
        if Student.objects.filter(user=user,is_active=False).exists():
            raise ValidationError("Deleted User!!!")
    return True


def create_auth_token(user):
    string_chars = string.ascii_lowercase + string.digits
    token = "".join(random.choice(string_chars) for _ in range(15))
    while UserAuthToken.objects.filter(key=token).exists():
        token = "".join(random.choice(string_chars) for _ in range(15))
    UserAuthToken.objects.filter(user=user).update(is_expired=True)
    user_auth_token = UserAuthToken(user=user, key=token, added_by=user)
    user_auth_token.save()
    return token


def login_success_data(user, token):
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
    return res

def validate_file_upload_request(exam_id, file):
    if exam_id in ['undefined', None, ""]:
        raise ValidationError("Choose an Examination!")
    if file in ['undefined', None, ""]:
        raise ValidationError("Choose a pdf file!")


def verify_file_type(file):
    file_extension = file.name.split('.')[-1]
    if file_extension != "pdf":
        raise ValidationError("Invalid file type")


def verify_document(page, exam):
    university = page.search("UNIVERSITY OF CALICUT")
    if university == []:
        return False

    sgpa = page.search("SGPA")
    if sgpa == []:
        return False

    verify_exam_marksheet_match(page, exam)

    marks_list = page.extract_table()
    marks_list_length = len(marks_list)
    if marks_list_length < 3 or marks_list_length > 9:
        return False

    return marks_list


def verify_exam_marksheet_match(page, exam):
    res = []
    if exam.exam_name == "Semester 1":
        res = page.search("I Semester")
    elif exam.exam_name == "Semester 2":
        res = page.search("II Semester")
    elif exam.exam_name == "Semester 3":
        res = page.search("III Semester")
    elif exam.exam_name == "Semester 4":
        res = page.search("IV Semester")
    elif exam.exam_name == "Semester 5":
        res = page.search("V Semester")
    elif exam.exam_name == "Semester 6":
        res = page.search("VI Semester")
    if len(res) == 0:
        raise ValidationError("Exam and Result Mismatch!")


def retreive_and_save_marks(user, file, exam, student):
    with pdfplumber.open(file) as pdf:
        first_page = pdf.pages[0]
        verified = verify_document(first_page,exam)
        if not verified:
            raise ValidationError("Invalid pdf")
        marks_list = verified
        
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
                
                if not failed:
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
                else:
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
