"""joanie URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, re_path

from drf_spectacular.views import (
    SpectacularJSONAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from joanie import admin_urls, client_urls, remote_endpoints_urls
from joanie.core.views import (
    BackOfficeRedirectView,
    CertificateVerificationView,
)
from joanie.debug import urls as debug_urls
from joanie.debug.views import SentryDecryptView
from joanie.edx_imports import urls as edx_imports_urls

API_VERSION = settings.API_VERSION

urlpatterns = (
    [
        path(
            "admin/sentry-decrypt", SentryDecryptView.as_view(), name="sentry-decrypt"
        ),
        path("admin/", admin.site.urls),
        re_path(
            r"^redirects/backoffice/(?P<path>.*)$",
            BackOfficeRedirectView.as_view(),
            name="redirect-to-backoffice",
        ),
    ]
    + admin_urls.urlpatterns
    + client_urls.urlpatterns
    + remote_endpoints_urls.urlpatterns
    + edx_imports_urls.urlpatterns
)

urlpatterns += i18n_patterns(
    path(
        "certificates/<uuid:certificate_id>",
        CertificateVerificationView.as_view(),
        name="certificate-verification",
    ),
)

if settings.DEBUG:
    urlpatterns += debug_urls.urlpatterns

if settings.USE_SWAGGER or settings.DEBUG:
    urlpatterns += (
        [
            path(
                f"{API_VERSION}/admin-swagger.json",
                SpectacularJSONAPIView.as_view(
                    api_version=API_VERSION,
                    urlconf="joanie.admin_urls",
                ),
                name="admin-api-schema",
            ),
            path(
                f"{API_VERSION}/admin-swagger/",
                SpectacularSwaggerView.as_view(url_name="admin-api-schema"),
                name="swagger-ui-schema",
            ),
            re_path(
                f"{API_VERSION}/admin-redoc/",
                SpectacularRedocView.as_view(url_name="admin-api-schema"),
                name="redoc-schema",
            ),
            path(
                f"{API_VERSION}/swagger.json",
                SpectacularJSONAPIView.as_view(
                    api_version=API_VERSION,
                    urlconf="joanie.client_urls",
                ),
                name="client-api-schema",
            ),
            path(
                f"{API_VERSION}/swagger/",
                SpectacularSwaggerView.as_view(url_name="client-api-schema"),
                name="swagger-ui-schema",
            ),
            re_path(
                f"{API_VERSION}/redoc/",
                SpectacularRedocView.as_view(url_name="client-api-schema"),
                name="redoc-schema",
            ),
        ]
        + staticfiles_urlpatterns()
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    )
