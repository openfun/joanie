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

from joanie.core import api
from joanie.core.views import (
    DebugMailSuccessPaymentViewHtml,
    DebugMailSuccessPaymentViewTxt,
)
from joanie.lms_handler.urls import urlpatterns as lms_urlpatterns
from joanie.payment.urls import urlpatterns as payment_urlpatterns

router = DefaultRouter()
router.register("addresses", api.AddressViewSet, basename="addresses")
router.register("certificates", api.CertificateViewSet, basename="certificates")
router.register("enrollments", api.EnrollmentViewSet, basename="enrollments")
router.register("orders", api.OrderViewSet, basename="orders")
router.register("course-runs", api.CourseRunViewSet, basename="course-runs")
router.register("products", api.ProductViewSet, basename="products")
router.register("wishlist", api.CourseWishViewSet, basename="wishlists")

API_VERSION = "v1.0"

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        f"api/{API_VERSION}/",
        include([*router.urls, *lms_urlpatterns, *payment_urlpatterns]),
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
