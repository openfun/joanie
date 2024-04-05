"""
API routes exposed for server to server. Requires a specific token to request.
"""

from django.conf import settings
from django.urls import path

from joanie.edx_imports.api import course_run_view

urlpatterns = [
    path(
        f"api/{settings.API_VERSION}/edx_imports/course-run/",
        course_run_view,
        name="edx_imports_course_run",
    )
]
