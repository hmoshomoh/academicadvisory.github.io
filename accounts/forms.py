from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from . import roles
from .models import Adviser, Student

BOOTSTRAP_INPUT = {"class": "form-control"}


class StudentRegistrationForm(UserCreationForm):
    """Self-registration. Every account created here joins the Student group."""

    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs=BOOTSTRAP_INPUT))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs=BOOTSTRAP_INPUT))
    email = forms.EmailField(widget=forms.EmailInput(attrs=BOOTSTRAP_INPUT))
    matric_number = forms.CharField(max_length=32, widget=forms.TextInput(attrs=BOOTSTRAP_INPUT))
    programme = forms.CharField(
        max_length=120, required=False, widget=forms.TextInput(attrs=BOOTSTRAP_INPUT)
    )
    adviser = forms.ModelChoiceField(
        queryset=Adviser.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Optional — an admin can assign one later.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("username", "password1", "password2"):
            self.fields[name].widget.attrs.update(BOOTSTRAP_INPUT)

    def clean_matric_number(self):
        value = self.cleaned_data["matric_number"].strip().upper()
        if Student.objects.filter(matric_number=value).exists():
            raise forms.ValidationError("That matriculation number is already registered.")
        return value

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.save()
        student_group = roles.ensure_groups()[0]
        user.groups.add(student_group)
        Student.objects.create(
            user=user,
            matric_number=self.cleaned_data["matric_number"],
            programme=self.cleaned_data.get("programme", ""),
            adviser=self.cleaned_data.get("adviser"),
        )
        return user


class BootstrapLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(BOOTSTRAP_INPUT)
