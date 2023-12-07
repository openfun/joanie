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
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path

from drf_spectacular.views import (
    SpectacularJSONAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from joanie import admin_urls, client_urls, remote_endpoints_urls
from joanie.core.views import (
    BackOfficeRedirectView,
    DebugCertificateTemplateView,
    DebugDegreeTemplateView,
    DebugMailSuccessPaymentViewHtml,
    DebugMailSuccessPaymentViewTxt,
)

API_VERSION = settings.API_VERSION

urlpatterns = (
    [
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
)

if settings.DEBUG:
    urlpatterns = (
        urlpatterns
        + [
            path("__debug__/", include("marion.urls.debug")),
            path(
                "__debug__/mail/order_validated_html",
                DebugMailSuccessPaymentViewHtml.as_view(),
                name="debug.mail.order_validated_html",
            ),
            path(
                "__debug__/mail/order_validated_txt",
                DebugMailSuccessPaymentViewTxt.as_view(),
                name="debug.mail.order_validated_txt",
            ),
            path(
                "__debug__/pdf-templates/certificate",
                DebugCertificateTemplateView.as_view(),
                name="debug.certificate_definition.certificate",
            ),
            path(
                "__debug__/pdf-templates/degree",
                DebugDegreeTemplateView.as_view(),
                name="debug.certificate_definition.degree",
            ),
        ]
        + staticfiles_urlpatterns()
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    )

if settings.USE_SWAGGER or settings.DEBUG:
    urlpatterns += [
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
