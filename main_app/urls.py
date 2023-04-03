from django.urls import path
from .views import (
    LoginView,
    LoginDataView,
    ChangePasswordView,
    StudentCreateViewFaculty,
    ExamDropdownViewStudent,
    SubjectDropdownViewStudent,
    StudentDropdownViewFaculty,
    MarkSheetFileUploadViewStudent,
    ViewMarkSheetView,
    ApproveMarklistView,
    StudentDetailView,
    SubjectWiseResultView,
    MarkSheetEditView,
    ConfirmMarkChangesView,
    StudentDeleteView,
)

urlpatterns = [
    # common
    path("login/", LoginView.as_view(), name="login"),
    path("login/data/", LoginDataView.as_view(), name="login_data"),
    path("change/password/", ChangePasswordView.as_view(), name="change_password"),
    path("marks/view/", ViewMarkSheetView.as_view(), name="marks_list"),
    path("dropdown/exam/", ExamDropdownViewStudent.as_view(), name="exam_dropdown"), # semester list

    # for faculty
    path("create/student/", StudentCreateViewFaculty.as_view(), name="create_student"),
    path("list/student/", StudentDropdownViewFaculty.as_view(), name="list_student"),
    path("marksheet/status/", ApproveMarklistView.as_view(), name="approve_marklist"),
    path("student/view/", StudentDetailView.as_view(), name="student_view"),
    path("dropdown/subject/", SubjectDropdownViewStudent.as_view(), name="subject_dropdown"),
    path("subject/result/", SubjectWiseResultView.as_view(), name="subject_result"),
    path("delete/student/", StudentDeleteView.as_view(), name="delete_student"),

    # for student
    path("upload/marksheet/", MarkSheetFileUploadViewStudent.as_view(), name="marksheet_file_upload"),
    path("mark/edit/", MarkSheetEditView.as_view(), name="marksheet_edit"),
    path("mark/confirm/", ConfirmMarkChangesView.as_view(), name="marksheet_confirm"),
]
