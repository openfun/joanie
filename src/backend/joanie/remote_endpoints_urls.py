"""
API routes exposed for server to server. Requires a specific token to request.
"""

from django.conf import settings
from django.urls import path

from joanie.core.api.remote_endpoints import (
    commercial_newsletter_subscription_webhook,
    enrollments_and_orders_on_course_run,
)

urlpatterns = [
    path(
        f"api/{settings.API_VERSION}/course-run-metrics/",
        enrollments_and_orders_on_course_run,
        name="enrollments_and_orders_on_course_run",
    ),
    path(
        f"api/{settings.API_VERSION}/newsletter-webhook/",
        commercial_newsletter_subscription_webhook,
        name="commercial_newsletter_subscription_webhook",
    ),
]
