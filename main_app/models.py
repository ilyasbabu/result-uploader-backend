from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


ROLE_CHOICES = (
    (1, "Admin"),
    (2, "Faculty"),
    (3, "Student"),
)


class User(AbstractUser):
    role = models.IntegerField(choices=ROLE_CHOICES, default=1)


class TimeStamp(models.Model):
    is_active = models.BooleanField(default=True)
    created_time = models.DateTimeField(auto_now_add=True)
    modified_time = models.DateTimeField(auto_now=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class UserAuthToken(TimeStamp):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="token_user")
    key = models.TextField()
    is_expired = models.BooleanField(default=False)

    class Meta:
        verbose_name = "UserAuthToken"
        verbose_name_plural = "UserAuthTokens"

    def __str__(self):
        return self.key

    def save(self, *args, **kwargs):
        """Overriding the default save method."""
        self.full_clean()
        return super().save(*args, **kwargs)


class Course(TimeStamp):
    course_name = models.CharField(max_length=255) # eg: BSC Computer Science

    def __str__(self):
        return self.course_name

class Exam(TimeStamp):
    exam_name = models.CharField(max_length=255) # eg: Semester Two Exam

    def __str__(self):
        return self.exam_name


class Subject(TimeStamp):
    subject_name = models.CharField(max_length=255) # eg: TRANSACTIONS: ESSENTIAL ENGLISH LANGUAGE SKILLS
    subject_code = models.CharField(max_length=255, null=True, blank=True) # eg: A01
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)

    def __str__(self):
        return self.subject_name


class Student(TimeStamp):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="student_user")
    registration_no = models.CharField(max_length=100, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username


class Faculty(TimeStamp):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="faculty_user")
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username


class Mark(TimeStamp):
    grade = models.CharField(max_length=10, null=True, blank=True)
    grade_point = models.IntegerField(null=True, blank=True)
    credit = models.IntegerField(null=True, blank=True)
    credit_point = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, null=True, blank=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.student.user.username) + " - " + str(self.subject.subject_name) + " - " + str(self.credit_point)


class MarkSheetDoc(TimeStamp):
    mark_sheet = models.FileField(upload_to="mark_sheet")
    sgpa = models.CharField(max_length=10, null=True, blank=True)
    status = models.CharField(max_length=10, default="Pending")
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.student.user.username) + " - " + str(self.exam.exam_name)
