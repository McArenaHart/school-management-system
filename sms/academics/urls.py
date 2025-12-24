from django.urls import path
from .views import (
    my_timetable,
    my_attendance,
    take_attendance_pick,
    take_attendance_mark,
    teacher_assessments,
    create_assessment,
    enter_grades,
    my_grades,
)

app_name = "academics"

urlpatterns = [
    path("timetable/", my_timetable, name="my_timetable"),

    path("attendance/my/", my_attendance, name="my_attendance"),
    path("attendance/take/", take_attendance_pick, name="take_attendance_pick"),
    path("attendance/take/mark/", take_attendance_mark, name="take_attendance_mark"),

    path("teacher/assessments/", teacher_assessments, name="teacher_assessments"),
    path("teacher/assessments/create/", create_assessment, name="create_assessment"),
    path("teacher/assessments/<int:assessment_id>/enter-grades/", enter_grades, name="enter_grades"),

    path("grades/my/", my_grades, name="my_grades"),
]
