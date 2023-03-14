from drf_yasg.inspectors import SwaggerAutoSchema
import drf_yasg.inspectors.base
import drf_yasg.openapi
import drf_yasg.utils

from joanie.core.viewsets import ActionSerializerType


def _call_view_method(
    view, method_name, fallback_attr=None, default=None, args=None, kwargs=None
):
    """Override of drf_yasg.inspectors.base.call_view_method to allow passing args."""
    if hasattr(view, method_name):
        try:
            view_method, is_callabale = drf_yasg.inspectors.base.is_callable_method(
                view, method_name
            )
            if is_callabale:
                args = args or []
                kwargs = kwargs or {}
                return view_method(*args, **kwargs)
        except Exception:  # pragma: no cover
            drf_yasg.inspectors.base.logger.warning(
                "view's %s raised exception during schema generation; use "
                "`getattr(self, 'swagger_fake_view', False)` to detect and short-circuit this",
                type(view).__name__,
                exc_info=True,
            )

    if fallback_attr and hasattr(view, fallback_attr):
        return getattr(view, fallback_attr)

    return default


class CustomAutoSchema(SwaggerAutoSchema):
    """
    SwaggerAutoSchema for viewsets with Request and Response serializers.
    https://github.com/axnsan12/drf-yasg/blob/master/src/drf_yasg/inspectors/view.py
    """

    def get_view_serializer(self, serializer_type):
        """Retrieve the serializer type"""
        return _call_view_method(
            self.view,
            "get_serializer",
            kwargs={"context": {"serializer_type": serializer_type}},
        )

    def get_request_serializer(self):
        """Retrieve Request serializer"""
        body_override = self._get_request_body_override()

        if body_override is None and self.method in self.implicit_body_methods:
            return _call_view_method(
                self.view,
                "get_serializer",
                kwargs={
                    "context": {"serializer_type": ActionSerializerType.REQUEST.value}
                },
            )

        if body_override is drf_yasg.utils.no_body:
            return None

        return body_override

    def get_default_response_serializer(self):
        """Retrieve Redsponse serializer"""
        body_override = self._get_request_body_override()
        if body_override and body_override is not drf_yasg.utils.no_body:
            return body_override

        return _call_view_method(
            self.view,
            "get_serializer",
            kwargs={
                "context": {"serializer_type": ActionSerializerType.RESPONSE.value}
            },
        )
