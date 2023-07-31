"""
Mixins for admin api
"""

from django.db import IntegrityError
from django.utils.translation import gettext_lazy as _

from rest_framework import mixins
from rest_framework.response import Response


class BulkDeleteMixin(mixins.DestroyModelMixin):
    """
    Mixin for classes that need to be able to bulk delete
    """

    def delete(self, request, *args, **kwargs):
        """
        Performs a deletion. Handles cases where an id is present
        in the url (single deletion), if no id is present in url
        and ids are in the body, performs bulk delete
        """

        if self.kwargs.get("id", None):
            return super().delete(request, *args, **kwargs)

        user = request.user
        id_to_delete = request.data.get("id", [])
        elements_to_delete = self.queryset.filter(id__in=id_to_delete)
        (deleted_elements, error_elements) = self.perform_bulk_delete(
            elements_to_delete, user
        )

        response = {}
        if len(deleted_elements) > 0:
            response["deleted"] = deleted_elements
        if len(error_elements) > 0:
            response["error"] = error_elements

        return Response(response)

    def perform_bulk_delete(self, instances, user):
        """
        Bulk deletion of model
        data = {"id": [<id_0>, <id_1>]}
        """
        error_elements = []
        deleted_elements = []
        for element in instances.all():
            if element.get_abilities(user)["delete"]:
                try:
                    deleted_element_id = element.id
                    element.delete()
                    deleted_elements.append(deleted_element_id)
                except IntegrityError as error:
                    error_elements.append(
                        {
                            "id": element.id,
                            "error": str(error),
                        }
                    )
            else:
                error_elements.append(
                    {
                        "id": element.id,
                        "error": _("Not authorized to delete this element"),
                    }
                )

        return (deleted_elements, error_elements)
