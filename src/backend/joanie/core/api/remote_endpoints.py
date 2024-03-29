"""
Remote endpoints API for other servers.
"""

from http import HTTPStatus

from django.conf import settings
from django.http import JsonResponse

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.request import Request
from rest_framework.response import Response

from joanie.core.models import User
from joanie.core.permissions import HasAPIKey
from joanie.core.utils.course_run import get_course_run_metrics
from joanie.core.utils.newsletter.subscription import (
    check_commercial_newsletter_subscription_webhook,
)


@api_view(["GET"])
@permission_classes([HasAPIKey])
@authentication_classes([])
def enrollments_and_orders_on_course_run(request: Request):
    """
    If the related course run is archived, return the amount of active enrollments and the amount
    of validated certificate orders.
    It requires an existing `resource_link` from an ended course run as input.

    Remote service must have its token set in Joanie's settings `JOANIE_AUTHORIZED_API_TOKENS`
    """
    resource_link = request.query_params.get("resource_link")
    if resource_link is None:
        return Response(
            {"detail": "Query parameter `resource_link` is required."},
            status=HTTPStatus.BAD_REQUEST,
        )

    response = get_course_run_metrics(resource_link=resource_link)

    return JsonResponse(response, status=HTTPStatus.OK)


@api_view(["POST"])
@permission_classes([HasAPIKey])
@authentication_classes([])
def commercial_newsletter_subscription_webhook(request: Request):
    """
    Webhook to handle newsletter subscription events.

    Remote service must have its token set in Joanie's settings `JOANIE_AUTHORIZED_API_TOKENS`
    """
    emails_to_check = []
    for event in request.data:
        if (
            settings.BREVO_COMMERCIAL_NEWSLETTER_LIST_ID in event["list_id"]
            and event["event"] == "unsubscribe"
            and User.objects.filter(email=event["email"]).exists()
        ):
            emails_to_check.append(event["email"])
    if emails_to_check:
        check_commercial_newsletter_subscription_webhook.delay(emails_to_check)
    return Response(status=HTTPStatus.OK)
