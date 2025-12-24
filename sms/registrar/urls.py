from django.urls import path
from .views import (
    admissions_list,
    apply,
    application_detail,
    mark_status,
    admit_application,
)

app_name = "registrar"

urlpatterns = [
    path("", admissions_list, name="admissions_list"),
    path("apply/", apply, name="apply"),
    path("application/<int:app_id>/", application_detail, name="application_detail"),
    path("application/<int:app_id>/status/<str:status>/", mark_status, name="mark_status"),
    path("application/<int:app_id>/admit/", admit_application, name="admit_application"),
]
