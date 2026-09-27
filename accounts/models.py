from django.conf import settings
from django.db import models


class Adviser(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="adviser"
    )
    staff_number = models.CharField(max_length=32, unique=True)
    department = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["staff_number"]

    def __str__(self):
        return "{} ({})".format(self.user.get_full_name() or self.user.username, self.staff_number)


class Student(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student"
    )
    matric_number = models.CharField(max_length=32, unique=True)
    programme = models.CharField(max_length=120, blank=True)
    adviser = models.ForeignKey(
        Adviser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_students",
    )

    class Meta:
        ordering = ["matric_number"]

    def __str__(self):
        return "{} ({})".format(self.user.get_full_name() or self.user.username, self.matric_number)

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username
