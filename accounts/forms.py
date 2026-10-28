from django import forms
from django.contrib.auth import authenticate
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

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

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

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username and password:
            raw_input = username.strip()
            # 1. Standard authentication by exact username
            self.user_cache = authenticate(self.request, username=raw_input, password=password)

            # 2. Matric-number or case-insensitive resolution
            if self.user_cache is None:
                # Match by matric number (e.g. "CSC/2022/001")
                student = Student.objects.filter(matric_number__iexact=raw_input).first()
                if not student:
                    # Match by normalized stripped matric (e.g. "CSC2022001" or "csc2022001")
                    stripped = raw_input.replace("/", "").lower()
                    student = Student.objects.filter(user__username__iexact=stripped).first()
                if student:
                    self.user_cache = authenticate(
                        self.request, username=student.user.username, password=password
                    )
                else:
                    # Match general user case-insensitively
                    user = User.objects.filter(username__iexact=raw_input).first()
                    if user:
                        self.user_cache = authenticate(
                            self.request, username=user.username, password=password
                        )

            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data
