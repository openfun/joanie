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
from joanie.lms_handler.urls import urlpatterns as lms_urlpatterns

router = DefaultRouter()
router.register("addresses", api.AddressViewSet, basename="addresses")
router.register("courses", api.CourseViewSet, basename="courses")
router.register("enrollments", api.EnrollmentViewSet, basename="enrollments")
router.register("orders", api.OrderViewSet, basename="orders")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include([*router.urls, *lms_urlpatterns])),
    path("api/documents/", include("marion.urls")),
]

if settings.DEBUG:
    urlpatterns = (
        urlpatterns
        + [path("__debug__/", include("marion.urls.debug"))]
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    )
