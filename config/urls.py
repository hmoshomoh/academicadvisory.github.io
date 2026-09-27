from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.static import serve

urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("accounts/", include("accounts.urls")),
    path("academics/", include("academics.urls")),
    path("complaints/", include("complaints.urls")),
    path("notifications/", include("notifications.urls")),
    path("django-admin/", admin.site.urls),
    # Complaint attachments are served by Django in both DEBUG and production.
    # That is enough for a college MVP on a single PaaS dyno; note that a PaaS
    # filesystem is ephemeral, so uploads do not survive a redeploy unless the
    # platform provides a persistent disk.
    re_path(
        r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}
    ),
]
