"""Serializers for Joanie's LMS handler."""

from django.utils.functional import lazy

from rest_framework import serializers

from joanie.core.enums import ALL_LANGUAGES
from joanie.core.models import CourseRun


class ListMultipleChoiceField(serializers.MultipleChoiceField):
    """
    Override DRF's MultipleChoiceField to represent it as a list.
    We don't want choices to render as a set e.g. {"en", "fr"}
    """

    def to_representation(self, value):
        return sorted(super().to_representation(value))


class SyncCourseRunSerializer(serializers.ModelSerializer):
    """
    Course run webhook serializer.
    """

    resource_link = serializers.CharField(max_length=200, required=True)
    languages = ListMultipleChoiceField(choices=lazy(lambda: ALL_LANGUAGES, tuple)())

    class Meta:
        model = CourseRun
        fields = [
            "resource_link",
            "start",
            "end",
            "enrollment_start",
            "enrollment_end",
            "languages",
        ]
        extra_kwargs = {"resource_link": {"required": True, "unique": False}}
