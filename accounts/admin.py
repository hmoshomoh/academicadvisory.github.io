from django.contrib import admin

from .models import Adviser, Student


@admin.register(Adviser)
class AdviserAdmin(admin.ModelAdmin):
    list_display = ["staff_number", "user", "department"]
    search_fields = ["staff_number", "user__username", "user__last_name"]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ["matric_number", "user", "programme", "adviser"]
    list_filter = ["adviser", "programme"]
    search_fields = ["matric_number", "user__username", "user__last_name"]
