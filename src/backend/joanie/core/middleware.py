"""Middleware for joanie project."""

import time

from dockerflow.django.middleware import DockerflowMiddleware


class JoanieDockerflowMiddleware(DockerflowMiddleware):
    """Override DockerflowMiddleware to change _build_extra_meta behaviour."""

    def _build_extra_meta(self, request):
        # ruff: noqa: SLF001
        # pylint: disable=protected-access
        """
        The access to request.user is removed to avoid creating unwanted user in
        database thought the DelegatedJWTAuthentication authentication backend.
        """
        out = {
            "errno": 0,
            "agent": request.META.get("HTTP_USER_AGENT", ""),
            "lang": request.META.get("HTTP_ACCEPT_LANGUAGE", ""),
            "method": request.method,
            "path": request.path,
        }

        # HACK: It's possible some other middleware has replaced the request we
        # modified earlier, so be sure to check for existence of these
        # attributes before trying to use them.
        if hasattr(request, "_id"):
            out["rid"] = request._id
        if hasattr(request, "_start_timestamp"):
            # Duration of request, in milliseconds.
            out["t"] = int(1000 * (time.time() - request._start_timestamp))

        return out
