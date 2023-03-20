from django.urls import path
from .views import (
    LoginView,
    LoginDataView,
    StudentCreateViewFaculty,
    ExamDropdownViewStudent,
    SubjectDropdownViewStudent,
    StudentDropdownViewFaculty,
    MarkSheetFileUploadViewStudent,
)

urlpatterns = [
    # common
    path("login/", LoginView.as_view(), name="login"),
    path("login/data/", LoginDataView.as_view(), name="login_data"),

    # for faculty
    path("create/student/", StudentCreateViewFaculty.as_view(), name="create_student"),
    path("list/student/", StudentDropdownViewFaculty.as_view(), name="list_student"),

    # for student
    path("dropdown/exam/", ExamDropdownViewStudent.as_view(), name="exam_dropdown"),
    path("dropdown/subject/", SubjectDropdownViewStudent.as_view(), name="subject_dropdown"),
    path("upload/marksheet/", MarkSheetFileUploadViewStudent.as_view(), name="marksheet_file_upload"),
]
