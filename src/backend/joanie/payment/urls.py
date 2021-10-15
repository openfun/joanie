"""
API routes exposed by our Payment app
"""
from django.urls import re_path

from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register("credit-cards", api.CreditCardViewSet, basename="credit-cards")
