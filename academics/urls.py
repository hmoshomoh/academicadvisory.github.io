from django.urls import path

from . import views

app_name = "academics"

urlpatterns = [
    path("me/", views.student_overview, name="student_overview"),
    path("me/advisory/new/", views.advisory_request_create, name="advisory_request_create"),
    path("advising/students/", views.adviser_students, name="adviser_students"),
    path("advising/students/<int:student_id>/", views.adviser_student_detail, name="adviser_student_detail"),
    path("advising/requests/", views.adviser_requests, name="adviser_requests"),
    path("advising/requests/<int:request_id>/respond/", views.advisory_respond, name="advisory_respond"),
]
