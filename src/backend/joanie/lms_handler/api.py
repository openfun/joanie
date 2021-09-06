"""
API endpoints
"""
import hashlib
import hmac

from django.conf import settings

from rest_framework.decorators import api_view
from rest_framework.response import Response

from joanie.core import models, utils
from joanie.lms_handler import LMSHandler


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
    msg = request.body.decode("utf-8")

    # Check if the provided signature is valid against any secret in our list
    #
    # We need to do this to support 2 or more versions of our infrastructure at the same time.
    # It then enables us to do updates and change the secret without incurring downtime.
    authorization_header = request.headers.get("Authorization")
    if not authorization_header:
        return Response("Missing authentication.", status=403)

    signature_is_valid = any(
        authorization_header
        == "SIG-HMAC-SHA256 {:s}".format(
            hmac.new(
                secret.encode("utf-8"),
                msg=msg.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).hexdigest()
        )
        for secret in getattr(settings, "JOANIE_COURSE_RUN_SYNC_SECRETS", [])
    )

    if not signature_is_valid:
        return Response("Invalid authentication.", status=401)

    # Select LMS from resource link
    resource_link = request.data.get("resource_link")
    if not resource_link:
        return Response({"resource_link": ["This field is required."]}, status=400)

    lms = LMSHandler.select_lms(resource_link)
    if lms is None:
        return Response(
            {"resource_link": ["No LMS configuration found for this resource link."]},
            status=400,
        )

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
        return Response(serializer.errors, status=400)

    if target_course_run:
        # Remove protected fields before update
        cleaned_data = lms.clean_course_run_data(serializer.validated_data)
        models.CourseRun.objects.filter(pk=target_course_run.pk).update(**cleaned_data)
    else:
        # Look for the course targeted by the resource link
        course_number = utils.normalize_code(lms.extract_course_number(request.data))
        try:
            course = models.Course.objects.get(code=course_number)
        except models.Course.DoesNotExist:
            return Response(
                {"resource_link": [f"Unknown course: {course_number:s}."]}, status=400
            )

        # Instantiate a new course run
        models.CourseRun.objects.create(**serializer.validated_data, course=course)

    return Response({"success": True})
