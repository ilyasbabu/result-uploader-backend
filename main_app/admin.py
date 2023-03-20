from django.contrib import admin
from .models import User, Course, Exam, Faculty, Mark, MarkSheetDoc, Student, Subject
from django.contrib.auth.admin import UserAdmin

# Register your models here.

# admin.site.register(User)
admin.site.register(Course)
admin.site.register(Exam)
admin.site.register(Faculty)
admin.site.register(Mark)
admin.site.register(MarkSheetDoc)
admin.site.register(Subject)
admin.site.register(Student)


@admin.register(User)
class CustomUserModelAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets+ (
        (                      
            'Role',
            {
                'fields': (
                    'role',
                ),
            },
        ),
    )
