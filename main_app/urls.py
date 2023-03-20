from django.urls import path
from .views import LoginView, StudentCreateView, ExamDropdownView, SubjectDropdownView

urlpatterns = [
    # common login
    path('login/',LoginView.as_view(),name='login'),

    # for faculty
    path('create/student/',StudentCreateView.as_view(),name='create_student'),

    # for student
    path('dropdown/exam/',ExamDropdownView.as_view(),name='exam_dropdown'),
    path('dropdown/subject/',SubjectDropdownView.as_view(),name='subject_dropdown'),
]