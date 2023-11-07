"""
API routes exposed by our Payment app
"""
from django.urls import re_path

from rest_framework.routers import DefaultRouter

from joanie.payment import api

router = DefaultRouter()
router.register("credit-cards", api.CreditCardViewSet, basename="credit-cards")

urlpatterns = router.urls + [
    re_path(r"payments/notifications/?$", api.webhook, name="payment_webhook"),
]
