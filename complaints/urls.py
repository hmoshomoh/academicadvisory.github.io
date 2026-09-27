from django.urls import path

from . import views

app_name = "complaints"

urlpatterns = [
    path("submit/", views.submit, name="submit"),
    path("submitted/<str:reference>/", views.submitted, name="submitted"),
    path("mine/", views.my_complaints, name="my_complaints"),
    path("mine/<int:pk>/", views.my_complaint_detail, name="my_complaint_detail"),
    path("track/", views.track, name="track"),
    path("manage/", views.admin_list, name="admin_list"),
    path("manage/<int:pk>/", views.admin_detail, name="admin_detail"),
    path("manage/<int:pk>/<str:action>/", views.admin_action, name="admin_action"),
    path("manage/dashboard/", views.dashboard, name="dashboard"),
    path("manage/export.csv", views.export_csv, name="export_csv"),
]
