from django.urls import path
from .views import (
    LoginView,
    LoginDataView,
    StudentCreateViewFaculty,
    ExamDropdownViewStudent,
    SubjectDropdownViewStudent,
    StudentDropdownViewFaculty,
    MarkSheetFileUploadViewStudent,
    ViewMarkSheetView,
)

urlpatterns = [
    # common
    path("login/", LoginView.as_view(), name="login"),
    path("login/data/", LoginDataView.as_view(), name="login_data"),
    path("marks/view/", ViewMarkSheetView.as_view(), name="marks_list"),
    path("dropdown/exam/", ExamDropdownViewStudent.as_view(), name="exam_dropdown"), # semester list

    # for faculty
    path("create/student/", StudentCreateViewFaculty.as_view(), name="create_student"),
    path("list/student/", StudentDropdownViewFaculty.as_view(), name="list_student"),

    # for student
    path("dropdown/subject/", SubjectDropdownViewStudent.as_view(), name="subject_dropdown"),
    path("upload/marksheet/", MarkSheetFileUploadViewStudent.as_view(), name="marksheet_file_upload"),
]
