"""
API routes exposed by our LMS handler app.
"""
from django.urls import re_path

from rest_framework import routers

from joanie.lms_handler.api import course_runs_sync, users_sync

ROUTER = routers.SimpleRouter()

urlpatterns = ROUTER.urls + [
    re_path("course-runs-sync/?$", course_runs_sync, name="course-runs-sync"),
    re_path("organizations-sync/?$", organizations_sync, name="organizations-sync"),
    re_path("users-sync/?$", users_sync, name="users-sync"),
]
