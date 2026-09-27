from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from . import roles
from .forms import BootstrapLoginForm, StudentRegistrationForm


class RoleLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = BootstrapLoginForm
    redirect_authenticated_user = True


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome — your student account is ready.")
            return redirect("accounts:dashboard")
    else:
        form = StudentRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard(request):
    """Single entry point after login; sends each role to its own dashboard."""
    role = roles.role_of(request.user)
    if role == roles.ADMIN:
        return redirect("complaints:admin_list")
    if role == roles.ADVISER:
        return redirect("academics:adviser_students")
    if role == roles.STUDENT:
        return redirect("academics:student_overview")
    return render(request, "accounts/no_role.html", status=403)
