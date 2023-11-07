"""
API routes exposed by our Signature app
"""
from django.urls import re_path

from rest_framework.routers import DefaultRouter

from joanie.signature import api

router = DefaultRouter()

urlpatterns = router.urls + [
    # Incoming webhook events from the signature provider
    re_path(
        r"signature/notifications/?$", api.webhook_signature, name="webhook_signature"
    ),
]
