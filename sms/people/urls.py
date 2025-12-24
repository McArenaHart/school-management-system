from django.urls import path
from .views import (
    my_students,
    link_student,
    student_detail,
    student_directory,
    settings_view,
)

app_name = "people"

urlpatterns = [
    path("", my_students, name="my_students"),
    path("link-student/", link_student, name="link_student"),
    path("student/<int:student_pk>/", student_detail, name="student_detail"),
    path("directory/", student_directory, name="student_directory"),
    path("settings/", settings_view, name="settings"),
]
