from django.urls import path
from .views import inbox, thread_detail, start_thread

app_name = "comms"

urlpatterns = [
    path("", inbox, name="inbox"),
    path("start/", start_thread, name="start_thread"),
    path("t/<int:thread_id>/", thread_detail, name="thread_detail"),
]
