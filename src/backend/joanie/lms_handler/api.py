"""
API endpoints
"""

from http import HTTPStatus

from rest_framework import exceptions
from rest_framework.decorators import api_view
from rest_framework.response import Response

from joanie.core import models, utils
from joanie.core.utils.signature import check_signature
from joanie.lms_handler import LMSHandler


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
    check_signature(request, "JOANIE_COURSE_RUN_SYNC_SECRETS")

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
    else:
        # Look for the course targeted by the resource link
        course_number = utils.normalize_code(lms.extract_course_number(request.data))
        try:
            course = models.Course.objects.get(code=course_number)
        except models.Course.DoesNotExist:
            course = models.Course.objects.create(
                code=course_number, title=request.data.get("title", course_number)
            )

        # Instantiate a new course run
        models.CourseRun.objects.create(**serializer.validated_data, course=course)

    return Response({"success": True})
