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

from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from joanie.core.api import admin as api_admin
from joanie.core.api import client as api_client
from joanie.core.views import (
    DebugMailSuccessPaymentViewHtml,
    DebugMailSuccessPaymentViewTxt,
)
from joanie.lms_handler.urls import urlpatterns as lms_urlpatterns
from joanie.payment.urls import urlpatterns as payment_urlpatterns

API_VERSION = "v1.0"

# 1) Client API

# - Main endpoints
router = DefaultRouter()
router.register("addresses", api_client.AddressViewSet, basename="addresses")
router.register("certificates", api_client.CertificateViewSet, basename="certificates")
router.register("courses", api_client.CourseViewSet, basename="courses")
router.register("course-runs", api_client.CourseRunViewSet, basename="course-runs")
router.register("enrollments", api_client.EnrollmentViewSet, basename="enrollments")
router.register("orders", api_client.OrderViewSet, basename="orders")
router.register(
    "organizations", api_client.OrganizationViewSet, basename="organizations"
)
router.register("products", api_client.ProductViewSet, basename="products")
router.register(
    "course-product-relations",
    api_client.CourseProductRelationViewSet,
    basename="course-product-relations",
)

# - Routes nested under a course
course_related_router = DefaultRouter()
course_related_router.register(
    "accesses",
    api_client.CourseAccessViewSet,
    basename="course_accesses",
)

# - Routes nested under an organization
organization_related_router = DefaultRouter()
organization_related_router.register(
    "accesses",
    api_client.OrganizationAccessViewSet,
    basename="organization_accesses",
)

# 2) Admin API
admin_router = DefaultRouter()
admin_router.register(
    "organizations", api_admin.OrganizationViewSet, basename="organizations"
)
admin_router.register("products", api_admin.ProductViewSet, basename="products")
admin_router.register("courses", api_admin.CourseViewSet, basename="courses")
admin_router.register("course-runs", api_admin.CourseRunViewSet, basename="course-runs")
admin_router.register(
    "certificate-definitions",
    api_admin.CertificateDefinitionViewSet,
    basename="certificate-definitions",
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        f"api/{API_VERSION}/admin/",
        include([*admin_router.urls]),
    ),
    path(
        f"api/{API_VERSION}/",
        include([*router.urls, *lms_urlpatterns, *payment_urlpatterns]),
    ),
    path(
        f"api/{API_VERSION}/courses/<uuid:course_id>/",
        include(course_related_router.urls),
    ),
    path(
        f"api/{API_VERSION}/organizations/<uuid:organization_id>/",
        include(organization_related_router.urls),
    ),
]

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
        ]
        + staticfiles_urlpatterns()
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    )

    try:
        # Try to import `drf_yasg` dynamically as this dependency is installed only
        # in a development context then configure schema views and routes
        from drf_yasg import openapi, views
    except ModuleNotFoundError:
        pass
    else:
        SchemaView = views.get_schema_view(
            openapi.Info(
                title="Joanie API",
                default_version=API_VERSION,
                description="This is the Joanie API schema.",
            ),
            public=True,
            permission_classes=[permissions.AllowAny],
        )

        urlpatterns += [
            re_path(
                rf"^{API_VERSION}/swagger(?P<format>\.json|\.yaml)$",
                SchemaView.without_ui(cache_timeout=0),
                name="api-schema",
            ),
            re_path(
                rf"^{API_VERSION}/swagger/$",
                SchemaView.with_ui("swagger", cache_timeout=0),
                name="swagger-ui-schema",
            ),
            re_path(
                rf"^{API_VERSION}/redoc/$",
                SchemaView.with_ui("redoc", cache_timeout=0),
                name="redoc-schema",
            ),
        ]
