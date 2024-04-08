"""Viewset for course_run in the edx_imports app."""

from http import HTTPStatus

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from joanie.core.models import CourseRun
from joanie.core.permissions import HasAPIKey
from joanie.core.serializers import AdminCourseRunSerializer


@api_view(["GET"])
@permission_classes([HasAPIKey])
@authentication_classes([])
def course_run_view(request: Request):
    """
    Look for first course_runs related to a resource_link.
    """
    resource_link = request.query_params.get("resource_link")
    if resource_link is None:
        return Response(
            {"detail": "Query parameter `resource_link` is required."},
            status=HTTPStatus.BAD_REQUEST,
        )

    course_run = get_object_or_404(CourseRun, resource_link__iexact=resource_link)

    if not course_run:
        return Response(
            {"detail": "Course run not found."},
            status=HTTPStatus.NOT_FOUND,
        )

    serializer = AdminCourseRunSerializer(course_run)

    return Response(serializer.data, status=HTTPStatus.OK)
