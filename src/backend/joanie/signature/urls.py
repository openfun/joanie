"""
API routes exposed by our Signature app
"""
from django.urls import re_path

from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()

urlpatterns = router.urls + [
    re_path(r"webhook-signature", api.webhook_signature, name="webhook_signature"),
]
