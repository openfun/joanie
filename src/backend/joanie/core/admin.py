from django.contrib import admin

from parler.admin import TranslatableAdmin

from . import models


@admin.register(models.CertificateDefinition)
class CertificateDefinitionAdmin(TranslatableAdmin):
    list_display = ('name', 'title')


@admin.register(models.Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('certificate_definition', 'order', 'issued_on')


@admin.register(models.Course)
class CourseAdmin(TranslatableAdmin):
    list_display = ('title', 'organization')


@admin.register(models.CourseRun)
class CourseRunAdmin(TranslatableAdmin):  # ReadOnly or not???
    list_display = ('title', 'resource_link')


@admin.register(models.Organization)
class OrganizationAdmin(TranslatableAdmin):
    list_display = ('title',)


@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username',)


@admin.register(models.Product)
class ProductAdmin(TranslatableAdmin):
    list_display = ('title', 'type')


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('owner', 'course_product', 'state')


@admin.register(models.ProductCourseRunPosition)
class ProductCourseRunPositionAdmin(admin.ModelAdmin):
    list_display = ('course_product', 'course_run', 'position')


@admin.register(models.Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('order', 'course_run', 'state')


@admin.register(models.CourseProduct)
class CourseProductAdmin(admin.ModelAdmin):
    list_display = ('product', 'course', 'price')
