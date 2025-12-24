from django.urls import path
from .views import (
    report_home,
    generate_report,
    report_pdf,
    dashboard
)

app_name = "reports"

urlpatterns = [
    path("", report_home, name="home"),
    path("generate/", generate_report, name="generate"),
    path("pdf/<int:student_id>/", report_pdf, name="pdf"),
    path("dashboard/", dashboard, name="dashboard"),
]
