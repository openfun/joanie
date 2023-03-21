from typing import Type
from enum import Enum

from rest_framework import serializers
from rest_framework.response import Response


class ActionSerializerType(Enum):
    REQUEST = "request"
    RESPONSE = "response"


class RequestResponseSerializersViewSetMixin:
    action_serializers: dict[str, dict[str, Type[serializers.Serializer]]] = {}

    def perform_create(self, serializer):
        return serializer.save()

    def perform_update(self, serializer):
        return serializer.save()

    def _create(self, request):
        """Use request and response serializers in create."""

        request_serializer = self.get_serializer(
            data=request.data,
            context={"serializer_type": ActionSerializerType.REQUEST.value},
        )
        request_serializer.is_valid(raise_exception=True)
        instance = self.perform_create(request_serializer)
        response_serializer = self.get_serializer(
            instance=instance,
            context={"serializer_type": ActionSerializerType.RESPONSE.value},
        )
        return Response(response_serializer.data, status=201)

    def _update(self, request, *args, **kwargs):
        """Use request and response serializers in update."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        request_serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
            context={"serializer_type": ActionSerializerType.REQUEST.value},
        )
        request_serializer.is_valid(raise_exception=True)
        self.perform_update(request_serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # invalidate prefetch catch to be sure that response
            # serializer fetch updated data
            instance._prefetched_objects_cache = {}

        response_serializer = self.get_serializer(
            instance=instance,
            context={"serializer_type": ActionSerializerType.RESPONSE.value},
        )
        return Response(response_serializer.data)

    def _get_action(self):
        if self.action == "partial_update":
            return "update"
        return self.action

    def get_request_serializer(self, *args, **kwargs):
        context = kwargs.get("context", {})
        context.update(
            {
                **self.get_serializer_context(),
                "serializer_type": ActionSerializerType.REQUEST.value,
            }
        )
        kwargs["context"] = context
        return self.get_serializer(*args, **kwargs)

    def get_response_serializer(self, *args, **kwargs):
        context = kwargs.get("context", {})
        context.update(
            {
                **self.get_serializer_context(),
                "serializer_type": ActionSerializerType.RESPONSE.value,
            }
        )
        kwargs["context"] = context
        return self.get_serializer(*args, **kwargs)

    def get_serializer(self, *args, **kwargs):
        context = kwargs.get("context", {})
        context.update(self.get_serializer_context())
        kwargs["context"] = context
        serializer_type = context.get("serializer_type")
        if serializer_type:
            serializer = self.action_serializers.get(self._get_action(), {}).get(
                serializer_type
            )
            if serializer:
                return serializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)
