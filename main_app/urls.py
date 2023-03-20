from django.urls import path
from .views import LoginView, StudentCreateView

urlpatterns = [
    path('login/',LoginView.as_view(),name='login'),
    path('create/student/',StudentCreateView.as_view(),name='create_student'),
]