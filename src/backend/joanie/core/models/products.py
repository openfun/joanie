import uuid

from django.db import models

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from parler import models as parler_models

from joanie.lms_handler import LMSHandler

from . import courses as courses_models
from . import customers as customers_models
from .. import enums
from .. import errors


class Product(parler_models.TranslatableModel):
    # uid used by cms to get order and enrollment
    uid = models.UUIDField(default=uuid.uuid4, unique=True)
    type = models.CharField(
        verbose_name=_("type"), choices=enums.PRODUCT_TYPE_CHOICES, max_length=50,
    )
    name = models.SlugField(verbose_name=_("name"), max_length=255, unique=True)
    translations = parler_models.TranslatedFields(
        title=models.CharField(verbose_name=_("title"), max_length=255),
        call_to_action_label=models.CharField(_("call to action label"), max_length=255),
    )

    class Meta:
        db_table = "joanie_product"
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def __str__(self):
        return f"Product \"{self.title}\" [{self.type}]"


class CourseProduct(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True)
    product = models.ForeignKey(Product, verbose_name=_("product"), on_delete=models.PROTECT)
    course = models.ForeignKey(
        courses_models.Course,
        related_name='course_products',
        verbose_name=_("course"),
        on_delete=models.PROTECT,
    )
    course_runs = models.ManyToManyField(courses_models.CourseRun)
    # TODO: check dans le resource_link si le course id correspond bien à tous les courses run
    # TODO: add currency info (settings? allow more than one device?)
    price = models.CharField(verbose_name=_("price"), blank=True, max_length=100)

    class Meta:
        db_table = "joanie_course_product"
        verbose_name = _("Course product")
        verbose_name_plural = _("Course products")
        unique_together = ('product', 'course')

    def __str__(self):
        return f"{self.product} for {self.course}"

    # TODO
    def cancel_order(self):
        pass
        # todo: passer en canceled order et enrollment

    def set_order(self, user, resource_links):
        # Check if an order for this CourseProduct already exists,
        # we create an other if only state is canceled
        # if user change his/her mind about course runs selected, the order has to be set to cancel
        # state and an other order has to be created
        orders = Order.objects.filter(course_product=self, owner=user)
        if (
                orders.exclude(
                    state__in=[enums.ORDER_STATE_CANCELED, enums.ORDER_STATE_FAILED],
                ).exists()
        ):
            raise errors.OrderAlreadyExists("Order already exist")

        # first create an order
        order = Order.objects.create(course_product=self, owner=user)
        for resource_link in resource_links:
            course_run = courses_models.CourseRun.objects.get(resource_link=resource_link)
            # associate each course run selected to the order
            order.course_runs.add(course_run)
            # then create enrollment for each course run
            enrollment = Enrollment.objects.create(course_run=course_run, order=order)
            # now we can enroll to LMS
            lms = LMSHandler.select_lms(resource_link)
            # if no lms found we set enrollment and order to failure state
            if lms is None:
                enrollment.state = enums.ENROLLMENT_STATE_FAILED
                enrollment.save()
                order.state = enums.ORDER_STATE_FAILED
                order.save()
                raise ValueError(f"No LMS configuration found for resource link: {resource_link}")
            # now set enrollment to lms and pass enrollment state to in_progress
            lms_enrollment = lms.set_enrollment(user.username, resource_link)
            if lms_enrollment['is_active']:
                enrollment.state = enums.ENROLLMENT_STATE_IN_PROGRESS
                enrollment.save()
        return order


class ProductCourseRunPosition(models.Model):
    course_product = models.ForeignKey(
        CourseProduct,
        related_name='course_runs_positions',
        verbose_name=_("course product"),
        on_delete=models.CASCADE,
    )
    position = models.PositiveSmallIntegerField(verbose_name=_("position in product"))
    course_run = models.ForeignKey(
        courses_models.CourseRun,
        verbose_name=_("course run"),
        on_delete=models.RESTRICT,
    )
    # ! check si 2 course run avec même position ils doivent avoir le même course_id
    # dans le resource_link
    # (organisation_courseid_sessionid)
    # la validation d'un des deux suffit pour passer au course run suivant ou à la certification

    class Meta:
        db_table = "joanie_product_course_run"
        verbose_name = _("Position of course runs in course product")
        verbose_name_plural = _("Positions of course runs in course product")

    def __str__(self):
        return f"{self.course_product}: {self.position}/ {self.course_run}]"


class Order(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True)
    course_product = models.ForeignKey(
        CourseProduct,
        verbose_name=_("course product"),
        related_name='orders',
        on_delete=models.RESTRICT,
    )
    course_runs = models.ManyToManyField(courses_models.CourseRun)
    # les commandes pourront être passées plus tard par les entreprises il faudra rajouter
    # un champ entreprise/ renommer owner en user ??
    # est-ce qu'on pointe vers un modèle intermédiaire owner qui peut etre un particulier
    # ou une entreprise ?
    owner = models.ForeignKey(
        customers_models.User, verbose_name=_("owner"),
        related_name='orders', on_delete=models.RESTRICT,
    )
    created_on = models.DateTimeField(_("created on"), default=timezone.now)
    state = models.CharField(  # use a number to easy queries???
        verbose_name=_("type"),
        choices=enums.ORDER_STATE_CHOICES,
        max_length=50,
        default=enums.ORDER_STATE_PENDING,
    )

    class Meta:
        db_table = "joanie_order"
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self):
        return f"Order for {self.course_product} and user {self.owner}"


class Enrollment(models.Model):
    course_run = models.ForeignKey(
        courses_models.CourseRun,
        verbose_name=_("course run"),
        on_delete=models.RESTRICT,
    )
    order = models.ForeignKey(Order, on_delete=models.RESTRICT)
    # course run state updated with elastic
    state = models.CharField(
        verbose_name=_("state"),
        choices=enums.ENROLLMENT_STATE_CHOICES,
        max_length=50,
        default=enums.ENROLLMENT_STATE_PENDING,
    )

    class Meta:
        db_table = "joanie_enrollment"
        verbose_name = _("Enrollment")
        verbose_name_plural = _("Enrollments")

    def __str__(self):
        return f"Enrollment for course run:{self.course_run} - order" \
               f"{self.order} [active: {self.is_active}/ state:{self.state}]"
