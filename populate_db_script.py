import os
import os.path
import json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'docomizer.settings')

import django
django.setup()

from django.db import transaction

from main_app.models import *



if __name__ == '__main__':
    print ('Starting database population...\n')
    # print ("Creating Admin User...")
    with transaction.atomic():
        # username = 'admin'
        # password = '1234'
        # email = 'admin@example.com'
        # first_name = 'admin'
        # last_name = ''
        # admin_user = User(
        #     username=username,
        #     email=email,
        #     first_name=first_name,
        #     last_name=last_name,
        #     is_superuser=True,
        #     is_staff=True,
        # )
        # admin_user.set_password(password)
        # admin_user.full_clean()
        # admin_user.save()
        # print ("admin credentials: \n username - "+username+"\n password - "+password)
        # print ("SuperAdmin User Created Sucessfully!!!\n")
        admin_user = User.objects.all()
        admin_user = admin_user[0]

        print ("Creating Exams...")
        semester_list = [
            "Semester 1",
            "Semester 2",
            "Semester 3",
            "Semester 4",
            "Semester 5",
            "Semester 6",
        ]
        for semester in semester_list:
            exam = Exam(
                exam_name=semester,
                added_by=admin_user
            )
            exam.full_clean()
            exam.save()
            print ("Exam - "+semester+" Created Successfully!")
        print ("Exams Created!\n")

        print("Creating Courses...")
        course_list = [
            "BSc Computer Science",
            "BSc Psychology",
            "BA History",
            "BCom (Commerce)",
            "BBA (Buisness Adminstration)",
            "BCA (Computer Application)",
            "BTHM (Hotel Management)",
        ]
        for course_name in course_list:
            course = Course(
                course_name=course_name,
                added_by=admin_user
            )
            course.full_clean()
            course.save()
            print ("Course - "+course_name+" Created Successfully!")
        print("Courses Created!\n")

        print ("Creating Demo Faculty...")
        faculty_user = User(
            username="faculty_user",
            email="faculty_user@example.com",
            first_name="Faculty",
            last_name="Faculty",
            role=2
        )
        faculty_user.set_password("123456")
        faculty_user.full_clean()
        faculty_user.save()
        faculty_course = Course.objects.filter(is_active=True)[0]
        faculty_profile = Faculty(
            user=faculty_user,
            course=faculty_course,
            added_by=admin_user
        )
        faculty_profile.full_clean()
        faculty_profile.save()
        print("Demo Faculty Created with username - 'faculty_user' and password - '12345'\n")
        print ("Initial Database Population Completed!")



