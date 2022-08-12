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
from django.urls import include, path

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
router.register("courses", api.CourseViewSet, basename="courses")
router.register("enrollments", api.EnrollmentViewSet, basename="enrollments")
router.register("orders", api.OrderViewSet, basename="orders")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include([*router.urls, *lms_urlpatterns, *payment_urlpatterns])),
]

if settings.DEBUG:
    urlpatterns = (
        urlpatterns
        + [
            path("__debug__/", include("marion.urls.debug")),
            path(
                "__debug__/mail/success_payment_html",
                DebugMailSuccessPaymentViewHtml.as_view(),
                name="debug.mail.success_payment_html",
            ),
            path(
                "__debug__/mail/success_payment_txt",
                DebugMailSuccessPaymentViewTxt.as_view(),
                name="debug.mail.success_payment_txt",
            ),
        ]
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    )
