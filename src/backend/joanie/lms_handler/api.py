"""
API endpoints
"""
import base64
import hashlib
import hmac
from http import HTTPStatus

from django.conf import settings
from django.core.files.base import ContentFile

from parler.utils import get_language_settings
from rest_framework import exceptions
from rest_framework.decorators import api_view
from rest_framework.response import Response

from joanie.core import models, utils
from joanie.lms_handler import LMSHandler


def authorize_request(request):
    """Check if the provided signature is valid against any secret in our list."""
    authorization_header = request.headers.get("Authorization")
    if not authorization_header:
        raise exceptions.PermissionDenied("Missing authentication.")

    if not any(
        authorization_header
        == "SIG-HMAC-SHA256 {:s}".format(  # pylint: disable = consider-using-f-string
            hmac.new(
                secret.encode("utf-8"),
                msg=request.body,
                digestmod=hashlib.sha256,
            ).hexdigest()
        )
        for secret in getattr(settings, "JOANIE_SYNC_SECRETS", [])
    ):
        raise exceptions.AuthenticationFailed("Invalid authentication.")


def detect_lms_from_resource_link(resource_link):
    """Detect the LMS from the resource link."""
    if not resource_link:
        raise exceptions.ValidationError({"resource_link": ["This field is required."]})

    lms = LMSHandler.select_lms(resource_link)
    if lms is None:
        raise exceptions.ValidationError(
            {"resource_link": ["No LMS configuration found for this resource link."]}
        )

    return lms


# pylint: disable=too-many-return-statements,unused-argument, too-many-locals,too-many-branches
@api_view(["POST"])
def course_runs_sync(request):
    """View for the web hook to create or update course runs based on their resource link.

    - A new course run is created or the existing course run is updated

    Parameters
    ----------
    request : Type[django.http.request.HttpRequest]
        The request on the API endpoint, it should contain a payload with course run fields.

    Returns
    -------
    Type[rest_framework.response.Response]
        HttpResponse acknowledging the success or failure of the synchronization operation.
    """
    authorize_request(request)

    # Select LMS from resource link
    resource_link = request.data.get("resource_link")
    lms = detect_lms_from_resource_link(resource_link)

    try:
        target_course_run = models.CourseRun.objects.only("pk").get(
            resource_link=resource_link
        )
    except models.CourseRun.DoesNotExist:
        target_course_run = None

    serializer = lms.get_course_run_serializer(
        request.data, partial=bool(target_course_run)
    )

    if serializer.is_valid() is not True:
        return Response(serializer.errors, status=HTTPStatus.BAD_REQUEST)

    if target_course_run:
        # Remove protected fields before update
        cleaned_data = lms.clean_course_run_data(serializer.validated_data)
        models.CourseRun.objects.filter(pk=target_course_run.pk).update(**cleaned_data)
        course_run = models.CourseRun.objects.get(pk=target_course_run.pk)
    else:
        # Look for the course targeted by the resource link
        course_number = utils.normalize_code(lms.extract_course_number(request.data))
        try:
            course = models.Course.objects.get(code=course_number)
        except models.Course.DoesNotExist:
            course = models.Course.objects.create(
                created_on=request.data.get("created_on"),
                code=course_number,
                title=request.data.get("title", course_number),
            )
            course.created_on = request.data.get("created_on")
            course.save()

        # Instantiate a new course run
        course_run = serializer.save(course=course)

    if title := request.data.get("title"):
        language_code = get_language_settings(
            str(serializer.validated_data["languages"])
        ).get("code")
        course_run.set_current_language(language_code)
        course_run.title = title
    course_run.created_on = request.data.get("created_on")
    course_run.save()

    return Response({"success": True})


@api_view(["POST"])
def organizations_sync(request):
    """View for the web hook to create or update organizations based on their resource link."""
    authorize_request(request)

    code = request.data.get("code")
    if not code:
        raise exceptions.ValidationError({"code": ["This field is required."]})
    code = utils.normalize_code(code)

    logo = None
    if (logo_base64 := request.data.get("logo_base64")) and (
        logo_name := request.data.get("logo_name")
    ):
        logo = ContentFile(base64.b64decode(logo_base64), logo_name)

    organization, created = models.Organization.objects.get_or_create(
        code=code,
        defaults={
            "title": request.data.get("title"),
            "logo": logo,
        },
    )

    if not created:
        organization.title = request.data.get("title")
        organization.logo = logo
        organization.save()

    return Response({"success": True})


@api_view(["POST"])
def users_sync(request):
    """View for the web hook to create or update users based on their resource link."""
    authorize_request(request)

    for user_data in request.data.get("users"):
        username = user_data.get("username")
        if username == "admin":
            continue

        if not username:
            raise exceptions.ValidationError({"username": ["This field is required."]})

        user, created = models.User.objects.get_or_create(
            username=username,
            defaults={
                "email": user_data.get("email"),
                "first_name": user_data.get("first_name"),
                "last_name": user_data.get("last_name"),
                "is_active": user_data.get("is_active"),
                "is_staff": user_data.get("is_staff"),
                "is_superuser": user_data.get("is_superuser"),
                "password": user_data.get("password"),
                "date_joined": user_data.get("date_joined"),
                "last_login": user_data.get("last_login"),
            },
        )

        if not created:
            user.email = user_data.get("email")
            user.first_name = user_data.get("first_name")
            user.last_name = user_data.get("last_name")
            user.is_active = user_data.get("is_active")
            user.is_staff = user_data.get("is_staff")
            user.is_superuser = user_data.get("is_superuser")
            user.password = user_data.get("password")
            user.date_joined = user_data.get("date_joined")
            user.last_login = user_data.get("last_login")
            user.save()

    return Response({"success": True})
