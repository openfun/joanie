# Create your models here.

from django.db import models

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from parler import models as parler_models


#from . import enums

# move to enums.py
PRODUCT_TYPE_CHOICES = (
    ('credential', _("Credential")),
    ('enrollment', _("Enrollment")),
    ('certificate', _("Certificate")),
)

ORDER_STATUS_CHOICES = (
    ('pending', _("Pending")),
    ('in_progress', _("In progress")),
    ('finished', _("Finished")),
)

ENROLLMENT_STATUS_CHOICES = (
    ('in_progress', _("In progress")),
    ('validated', _("Validated")),
    ('failed', _("Failed")),
)


class Course(models.Model):
    """ A new course created will initialize a cms page """
    code = models.CharField(verbose_name=_("reference to cms page"), blank=True, max_length=100)
    title = models.CharField(verbose_name=_("title"), max_length=255) # will be used to generate a slug name of cms page


class Certification(models.Model):
    """ Certificate definition """
    name = models.SlugField(verbose_name=_("name"), max_length=255, unique=True)
    title = models.CharField(verbose_name=_("title"), max_length=255)
    description = models.TextField(verbose_name=_("description"), max_length=500)
    # howard template used to generate pdf certificate
    template = models.CharField(verbose_name=_("template to generate pdf"))  # ??


class Product(models.Model):
    type = models.CharField(verbose_name=_("type"), choices=PRODUCT_TYPE_CHOICES, max_length=50)
    name = models.SlugField(verbose_name=_("name"), max_length=255, unique=True)
    title = models.CharField(verbose_name=_("title"), max_length=255)
    price = models.CharField(verbose_name=_("price"), blank=True, max_length=100)
    course = models.ForeignKey(Course, verbose_name=_("course"))  # link between cms page and product
    call_to_action_label = parler_models.TranslatedField(any_language=True)


class ProductCertification(models.Model):
    product = models.ForeignKey(Product, verbose_name=_("product"))
    certification = models.ForeignKey(Certification, verbose_name=_("certification"))
    # NB: add check product types allowed


class User(models.Model):
    username = models.CharField(_("username"), max_length=255, unique=True)
    payment_token = "" # ???


class Order(models.Model):
    product = models.ForeignKey(Product, verbose_name=_("product"), related_name='orders')
    owner = models.ForeignKey(User, verbose_name=_("owner"), related_name='orders', on_delete=models.CASCADE)
    creation_date = models.DateTimeField(_("creation date"), default=timezone.now)
    status = models.CharField(verbose_name=_("type"), choices=ORDER_STATUS_CHOICES, max_length=50)
    # use a number to easy queries ?


class CourseRun(models.Model):
    resource_link = ""  #....
    start = models.DateTimeField(_("start date"))
    end = models.DateTimeField(_("end date"))
    enrollment_start = models.DateTimeField(_("enrollment date"), null=True)
    enrollment_end = models.DateTimeField(_("enrollment end"), null=True)


class ProductCourseRun(models.Model):
    product = models.ForeignKey(
        Product, related_name='course_runs', verbose_name=_("training product"), on_delete=models.CASCADE,
    )
    position = models.PositiveSmallIntegerField(verbose_name=_("position in training product"))
    course_run = models.ForeignKey(CourseRun, verbose_name=_("course run"))


class Enrollment(models.Model):
    course_run = models.ForeignKey(CourseRun)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    status = models.CharField(verbose_name=_("status"), choices=ENROLLMENT_STATUS_CHOICES)  # update with elastic
    is_active = models.BooleanField(default=False) # inscrit ou pas (désabonnement/expiration)


class Certificate(models.Model):
    certification = models.ForeignKey(Certification, related_name='certificates_issued')
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    attachment = models.FileField() # ? pdf generated with marion
    issue_date = models.DateTimeField(_("issue date"), default=timezone.now)

