"""
Declare and configure the models for the courses part
"""
from collections.abc import Mapping
from datetime import MAXYEAR, datetime, timezone

from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.utils import timezone as django_timezone
from django.utils.functional import lazy
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _

from easy_thumbnails.fields import ThumbnailerImageField
from parler import models as parler_models
from rest_framework.reverse import reverse
from url_normalize import url_normalize

from joanie.core import enums, utils
from joanie.core.fields.multiselect import MultiSelectField
from joanie.core.utils import webhooks

from .accounts import User
from .base import BaseModel

MAX_DATE = datetime(MAXYEAR, 12, 31, tzinfo=timezone.utc)


class CourseState(Mapping):
    """An immutable object to describe a course (resp. course run) state."""

    (
        ONGOING_OPEN,
        FUTURE_OPEN,
        ARCHIVED_OPEN,
        FUTURE_NOT_YET_OPEN,
        FUTURE_CLOSED,
        ONGOING_CLOSED,
        ARCHIVED_CLOSED,
        TO_BE_SCHEDULED,
    ) = range(8)

    STATE_CALLS_TO_ACTION = {
        ONGOING_OPEN: _("enroll now"),
        FUTURE_OPEN: _("enroll now"),
        ARCHIVED_OPEN: _("study now"),
        FUTURE_NOT_YET_OPEN: None,
        FUTURE_CLOSED: None,
        ONGOING_CLOSED: None,
        ARCHIVED_CLOSED: None,
        TO_BE_SCHEDULED: None,
    }

    STATE_TEXTS = {
        ONGOING_OPEN: _("closing on"),
        FUTURE_OPEN: _("starting on"),
        ARCHIVED_OPEN: _("closing on"),
        FUTURE_NOT_YET_OPEN: _("starting on"),
        FUTURE_CLOSED: _("enrollment closed"),
        ONGOING_CLOSED: _("on-going"),
        ARCHIVED_CLOSED: _("archived"),
        TO_BE_SCHEDULED: _("to be scheduled"),
    }

    def __init__(self, priority, date_time=None):
        """
        Initialize a course state with a priority and optionally a datetime.

        Several states are possible for a course run each of which is given a priority. The
        lower the priority, the more interesting the course run is (a course run open for
        enrollment is more interesting than an archived course run):
        - 0 | ONGOING_OPEN: a run is ongoing and open for enrollment
              > "closing on": {enrollment_end}
        - 1 | FUTURE_OPEN: a run is future and open for enrollment > "starting on": {start}
        - 2 | ARCHIVED_OPEN: a run is past but open for enrollment > "closing on": {enrollment_end}
        - 3 | FUTURE_NOT_YET_OPEN: a run is future and not yet open for enrollment
              > "starting on": {start}
        - 4 | FUTURE_CLOSED: a run is future and no more open for enrollment > "closed": {None}
        - 5 | ONGOING_CLOSED: a run is ongoing but closed for enrollment > "on going": {None}
        - 6 | ARCHIVED_CLOSED: there's a finished run in the past > "archived": {None}
        - 7 | TO_BE_SCHEDULED: there is no run with a start date or no run at all
              > "to be scheduled": {None}
        """
        # Check that `date_time` is set when it should be
        if date_time is None and priority in [
            CourseState.ONGOING_OPEN,
            CourseState.FUTURE_OPEN,
            CourseState.ARCHIVED_OPEN,
            CourseState.FUTURE_NOT_YET_OPEN,
        ]:
            raise ValidationError(
                f"date_time should not be null for a {priority:d} course state."
            )

        # A special case of being open is when enrollment never ends
        text = self.STATE_TEXTS[priority]
        if (
            priority in [CourseState.ONGOING_OPEN, CourseState.ARCHIVED_OPEN]
            and date_time.year == MAXYEAR
        ):
            text = _("forever open")
            date_time = None
        kwargs = {
            "priority": priority,
            "datetime": date_time,
            "call_to_action": self.STATE_CALLS_TO_ACTION[priority],
            "text": text,
        }
        self._d = {**kwargs}

    def __str__(self):
        """String representation"""
        return str(self._d["text"])

    def __iter__(self):
        """Iterate on the inner dictionary."""
        return iter(self._d)

    def __len__(self):
        """Return length of the inner dictionary."""
        return len(self._d)

    def __getitem__(self, key):
        """Access the inner dictionary."""
        return self._d[key]

    def __lt__(self, other):
        """Make it easy to compare two course states."""
        return self._d["priority"] < other["priority"]


class Organization(parler_models.TranslatableModel, BaseModel):
    """
    Organization model represents and records entities that manage courses.
    It could be a university or a training company for example.
    It's required to create course page in cms.
    It will allow to validate user enrollment to course or not, depending on various criteria.
    """

    code = models.CharField(_("code"), unique=True, db_index=True, max_length=100)
    translations = parler_models.TranslatedFields(
        title=models.CharField(_("title"), max_length=255)
    )
    representative = models.CharField(
        _("representative"),
        help_text=_("representative fullname (to sign certificate for example)"),
        max_length=100,
        blank=True,
    )
    signature = models.ImageField(_("signature"), blank=True)
    logo = ThumbnailerImageField(_("logo"), blank=True)

    class Meta:
        db_table = "joanie_organization"
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")
        ordering = ["-created_on"]

    def __str__(self):
        return (
            f"[{self.code}] {self.safe_translation_getter('title', any_language=True)}"
        )

    def clean(self):
        """
        We normalize the code with slugify for better uniqueness
        """
        # Normalize the code by slugifying and capitalizing it
        self.code = utils.normalize_code(self.code)
        return super().clean()

    def get_abilities(self, user):
        """
        Compute and return abilities for a given user taking into account
        the current state of the object.
        """
        is_owner_or_admin = False
        role = None

        if user.is_authenticated:
            try:
                role = self.user_role
            except AttributeError:
                try:
                    role = self.accesses.filter(user=user).values("role")[0]["role"]
                except (OrganizationAccess.DoesNotExist, IndexError):
                    role = None

            is_owner_or_admin = role in [enums.OWNER, enums.ADMIN]

        return {
            "get": True,
            "patch": is_owner_or_admin,
            "put": is_owner_or_admin,
            "delete": role == enums.OWNER,
            "manage_accesses": is_owner_or_admin,
        }


class OrganizationAccess(BaseModel):
    """Link table between organizations and users"""

    ROLE_CHOICES = (
        (enums.OWNER, _("owner")),
        (enums.ADMIN, _("administrator")),
        (enums.MEMBER, _("member")),
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="accesses",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="organization_accesses"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=enums.MEMBER)

    class Meta:
        db_table = "joanie_organization_access"
        verbose_name = _("Organization access")
        verbose_name_plural = _("Organization accesses")
        unique_together = ("organization", "user")
        ordering = ["-created_on"]

    def __str__(self):
        role = capfirst(self.get_role_display())
        return (
            f"{role:s} role for {self.user.username:s} on {self.organization.title:s}"
        )

    def save(self, *args, **kwargs):
        """Make sure we keep at least one owner for the organization."""
        if self.pk and self.role != enums.OWNER:
            accesses = self._meta.model.objects.filter(
                organization=self.organization, role=enums.OWNER
            ).only("pk")
            if len(accesses) == 1 and accesses[0].pk == self.pk:
                raise PermissionDenied(
                    "An organization should keep at least one owner."
                )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Disallow deleting the last owner."""
        if (
            self.role == enums.OWNER
            and self._meta.model.objects.filter(
                organization=self.organization, role=enums.OWNER
            ).count()
            == 1
        ):
            raise PermissionDenied("An organization should keep at least one owner.")
        return super().delete(*args, **kwargs)

    def get_abilities(self, user):
        """
        Compute and return abilities for a given user taking into account
        the current state of the object.
        """
        is_organization_owner_or_admin = False
        role = None

        if user.is_authenticated:
            try:
                role = self.user_role
            except AttributeError:
                try:
                    role = self._meta.model.objects.filter(
                        organization=self.organization_id, user=user
                    ).values("role")[0]["role"]
                except (OrganizationAccess.DoesNotExist, IndexError):
                    role = None

            is_organization_owner_or_admin = role in [enums.OWNER, enums.ADMIN]

        if self.role == enums.OWNER:
            can_delete = (
                user.id == self.user_id
                and self.organization.accesses.filter(role=enums.OWNER).count() > 1
            )
            set_role_to = [enums.ADMIN, enums.MEMBER] if can_delete else []
        else:
            can_delete = is_organization_owner_or_admin
            set_role_to = []
            if role == enums.OWNER:
                set_role_to.append(enums.OWNER)
            if is_organization_owner_or_admin:
                set_role_to.extend([enums.ADMIN, enums.MEMBER])

        # Remove the current role as we don't want to propose it as an option
        try:
            set_role_to.remove(self.role)
        except ValueError:
            pass

        return {
            "delete": can_delete,
            "get": bool(role),
            "patch": bool(set_role_to),
            "put": bool(set_role_to),
            "set_role_to": set_role_to,
        }


class Course(parler_models.TranslatableModel, BaseModel):
    """
    Course model represents and records a course in the cms catalog.
    A new course created will initialize a cms page.
    """

    code = models.CharField(_("code"), max_length=100, unique=True, db_index=True)
    cover = ThumbnailerImageField(_("cover"), blank=True)
    translations = parler_models.TranslatedFields(
        title=models.CharField(_("title"), max_length=255)
    )
    organizations = models.ManyToManyField(
        to=Organization,
        related_name="courses",
        verbose_name=_("organizations"),
    )
    products = models.ManyToManyField(
        "Product",
        related_name="courses",
        through="CourseProductRelation",
        through_fields=("course", "product"),
        verbose_name=_("products"),
        blank=True,
    )

    class Meta:
        db_table = "joanie_course"
        ordering = ("code",)
        verbose_name = _("Course")
        verbose_name_plural = _("Courses")

    def __str__(self):
        return self.safe_translation_getter("title", any_language=True)

    @property
    def state(self):
        """
        The state of the course carrying information on what to display on a course glimpse.

        The game is to find the highest priority state for this course among its course runs.
        """
        # The default state is for a course that has no course runs
        best_state = CourseState(CourseState.TO_BE_SCHEDULED)

        for course_run in self.course_runs.only(
            "start", "end", "enrollment_start", "enrollment_end"
        ):
            state = course_run.state
            if state < best_state:
                best_state = state
            if state["priority"] == CourseState.ONGOING_OPEN:
                # We found the best state, don't waste more time
                break

        return best_state

    def clean(self):
        """
        We normalize the code with slugify for better uniqueness
        """
        # Normalize the code by slugifying and capitalizing it
        self.code = utils.normalize_code(self.code)
        return super().clean()

    def get_selling_organizations(self, product=None):
        """
        Return the list of organizations selling a product for the course.
        If no product is provided, return the list of organizations selling
        any product for the course.
        """

        if product is None:
            qs = self.product_relations.all()
        else:
            qs = self.product_relations.filter(product=product)

        return Organization.objects.filter(
            id__in=qs.distinct()
            .only("organizations")
            .values_list("organizations", flat=True)
        )

    def get_abilities(self, user):
        """
        Compute and return abilities for a given user taking into account
        the current state of the object.
        """
        is_owner_or_admin = False
        role = None

        if user.is_authenticated:
            try:
                role = self.user_role
            except AttributeError:
                try:
                    role = self.accesses.filter(user=user).values("role")[0]["role"]
                except (CourseAccess.DoesNotExist, IndexError):
                    role = None

            is_owner_or_admin = role in [enums.OWNER, enums.ADMIN]

        return {
            "get": True,
            "patch": is_owner_or_admin,
            "put": is_owner_or_admin,
            "delete": role == enums.OWNER,
            "manage_accesses": is_owner_or_admin,
        }


class CourseAccess(BaseModel):
    """Link table between courses and users"""

    ROLE_CHOICES = (
        (enums.OWNER, _("owner")),
        (enums.ADMIN, _("administrator")),
        (enums.INSTRUCTOR, _("instructor")),
        (enums.MANAGER, _("manager")),
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="accesses",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="course_accesses"
    )
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default=enums.INSTRUCTOR
    )

    class Meta:
        db_table = "joanie_course_access"
        verbose_name = _("Course access")
        verbose_name_plural = _("Course accesses")
        unique_together = ("course", "user")
        ordering = ["-created_on"]

    def __str__(self):
        role = capfirst(self.get_role_display())
        return f"{role:s} role for {self.user.username:s} on {self.course.title:s}"

    def save(self, *args, **kwargs):
        """Make sure we keep at least one owner for the course."""
        if self.pk and self.role != enums.OWNER:
            accesses = self._meta.model.objects.filter(
                course=self.course, role=enums.OWNER
            ).only("pk")
            if len(accesses) == 1 and accesses[0].pk == self.pk:
                raise PermissionDenied("A course should keep at least one owner.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Disallow deleting the last owner."""
        if (
            self.role == enums.OWNER
            and self._meta.model.objects.filter(
                course=self.course, role=enums.OWNER
            ).count()
            == 1
        ):
            raise PermissionDenied("A course should keep at least one owner.")
        return super().delete(*args, **kwargs)

    def get_abilities(self, user):
        """
        Compute and return abilities for a given user taking into account
        the current state of the object.
        """
        is_course_owner_or_admin = False
        role = None

        if user.is_authenticated:
            try:
                role = self.user_role
            except AttributeError:
                try:
                    role = self._meta.model.objects.filter(
                        course=self.course_id, user=user
                    ).values("role")[0]["role"]
                except (CourseAccess.DoesNotExist, IndexError):
                    role = None

            is_course_owner_or_admin = role in [enums.OWNER, enums.ADMIN]

        if self.role == enums.OWNER:
            can_delete = (
                user.id == self.user_id
                and self.course.accesses.filter(role=enums.OWNER).count() > 1
            )
            set_role_to = (
                [enums.ADMIN, enums.INSTRUCTOR, enums.MANAGER] if can_delete else []
            )
        else:
            can_delete = is_course_owner_or_admin
            set_role_to = []
            if role == enums.OWNER:
                set_role_to.append(enums.OWNER)
            if is_course_owner_or_admin:
                set_role_to.extend([enums.ADMIN, enums.INSTRUCTOR, enums.MANAGER])

        # Remove the current role as we don't want to propose it as an option
        try:
            set_role_to.remove(self.role)
        except ValueError:
            pass

        return {
            "delete": can_delete,
            "get": bool(role),
            "patch": bool(set_role_to),
            "put": bool(set_role_to),
            "set_role_to": set_role_to,
        }


class CourseProductRelation(BaseModel):
    """
    CourseProductRelation model allows defining the products sold on a given course.

    It is used as through model in a ManyToMany relation between a Course and a Product.

    The `organizations` field defines what organizations are selling the product on the
    course. If several organizations are selling a product on a course, the buyer is asked
    to choose from which organization they want to buy it.
    """

    course = models.ForeignKey(
        to=Course,
        verbose_name=_("course"),
        related_name="product_relations",
        on_delete=models.RESTRICT,
    )
    product = models.ForeignKey(
        to="Product",
        verbose_name=_("product"),
        related_name="course_relations",
        on_delete=models.CASCADE,
    )
    organizations = models.ManyToManyField(
        to=Organization,
        related_name="product_relations",
        verbose_name=_("organizations"),
    )

    class Meta:
        db_table = "joanie_course_product_relation"
        unique_together = ("product", "course")
        verbose_name = _("Course relation to a product")
        verbose_name_plural = _("Courses relations to products")

    def __str__(self):
        return f"{self.course}: {self.product}"


class CourseRun(parler_models.TranslatableModel, BaseModel):
    """
    Course run represents and records the occurrence of a course between a start
    and an end date.
    """

    course = models.ForeignKey(
        to=Course,
        on_delete=models.PROTECT,
        related_name="course_runs",
        verbose_name=_("course"),
    )

    # link to lms resource
    resource_link = models.CharField(_("resource link"), max_length=200, unique=True)
    translations = parler_models.TranslatedFields(
        title=models.CharField(_("title"), max_length=255)
    )
    # availability period
    start = models.DateTimeField(_("course start"), blank=True, null=True)
    end = models.DateTimeField(_("course end"), blank=True, null=True)
    # enrollment allowed period
    enrollment_start = models.DateTimeField(_("enrollment date"), blank=True, null=True)
    enrollment_end = models.DateTimeField(_("enrollment end"), blank=True, null=True)
    languages = MultiSelectField(
        max_choices=50,
        max_length=255,  # MySQL does not allow max_length > 255
        # Language choices are made lazy so that we can override them in our tests.
        # When set directly, they are evaluated too early and can't be changed with the
        # "override_settings" utility.
        choices=lazy(lambda: enums.ALL_LANGUAGES, tuple)(),
        help_text=_("The list of languages in which the course content is available."),
    )
    is_gradable = models.BooleanField(_("is gradable"), default=False)
    is_listed = models.BooleanField(
        _("is listed"),
        default=False,
        help_text=_(
            "If checked the course run will be included in the list of course runs "
            "available for enrollment on the related course page."
        ),
    )

    class Meta:
        db_table = "joanie_course_run"
        verbose_name = _("Course run")
        verbose_name_plural = _("Course runs")
        ordering = ["-created_on"]

    def __str__(self):
        return (
            f"{self.safe_translation_getter('title', any_language=True)} "
            f"[{self.state.get('text')}]"
        )

    def get_serialized(self, visibility=None):
        """
        Return data for the course run that will be sent to the remote web hooks.
        Course run visibility can be forced via the eponym argument.
        """
        site = Site.objects.get_current()
        resource_path = reverse("course-runs-detail", kwargs={"id": self.id})
        if (
            visibility is not None
            and visibility not in enums.CATALOG_VISIBILITY_CHOICES
        ):
            raise ValueError(
                f"Invalid visibility: {visibility}. Must be one "
                f"of {enums.CATALOG_VISIBILITY_CHOICES} or None"
            )

        return {
            "catalog_visibility": visibility
            or (enums.COURSE_AND_SEARCH if self.is_listed else enums.HIDDEN),
            "course": self.course.code,
            "end": self.end.isoformat() if self.end else None,
            "enrollment_start": self.enrollment_start.isoformat()
            if self.enrollment_start
            else None,
            "enrollment_end": self.enrollment_end.isoformat()
            if self.enrollment_end
            else None,
            "languages": self.languages,
            "resource_link": f"https://{site.domain:s}{resource_path:s}",
            "start": self.start.isoformat() if self.start else None,
        }

    # pylint: disable=invalid-name
    def get_equivalent_serialized_course_runs_for_related_products(
        self, visibility=None
    ):
        """
        Returns the equivalent serialized course runs for the products related to the
        current course run.
        """
        products = self.course.products.model.objects.filter(
            models.Q(target_course_relations__course_runs__isnull=True)
            | models.Q(target_course_relations__course_runs=self),
            target_course_relations__course=self.course,
        )
        return self.course.products.model.get_equivalent_serialized_course_runs_for_products(
            products, visibility=visibility
        )

    # pylint: disable=too-many-return-statements
    @staticmethod
    def compute_state(start, end, enrollment_start, enrollment_end):
        """
        Compute at the current time the state of a course run that would have the dates
        passed in argument.

        A static method not using the instance allows to call it with an Elasticsearch result.
        """
        if not start or not enrollment_start:
            return CourseState(CourseState.TO_BE_SCHEDULED)

        # course run end dates are not required and should default to forever
        # e.g. a course run with no end date is presumed to be always on-going
        end = end or MAX_DATE
        enrollment_end = enrollment_end or MAX_DATE

        now = django_timezone.now()
        if start < now:
            if end > now:
                if enrollment_end > now:
                    # ongoing open
                    return CourseState(CourseState.ONGOING_OPEN, enrollment_end)
                # ongoing closed
                return CourseState(CourseState.ONGOING_CLOSED)
            if enrollment_start < now < enrollment_end:
                # archived open
                return CourseState(CourseState.ARCHIVED_OPEN, enrollment_end)
            # archived closed
            return CourseState(CourseState.ARCHIVED_CLOSED)
        if enrollment_start > now:
            # future not yet open
            return CourseState(CourseState.FUTURE_NOT_YET_OPEN, start)
        if enrollment_end > now:
            # future open
            return CourseState(CourseState.FUTURE_OPEN, start)
        # future already closed
        return CourseState(CourseState.FUTURE_CLOSED)

    @property
    def state(self):
        """Return the state of the course run at the current time."""
        return self.compute_state(
            self.start, self.end, self.enrollment_start, self.enrollment_end
        )

    def clean(self):
        """
        Normalize the resource_link url and prevent data integrity error when course is
        updated.
        """
        self.resource_link = url_normalize(self.resource_link)

        # If the course run is updating and the course field has changed ...
        if self.created_on:
            old_course_id = (
                CourseRun.objects.only("course_id").get(pk=self.pk).course_id
            )
            if old_course_id != self.course_id:
                # ... Check the course run instance does not rely on product/order relations
                if (
                    self.product_relations.count() > 0
                    or self.order_relations.count() > 0
                ):
                    raise ValidationError(
                        _(
                            "This course run relies on a product relation. "
                            "So you cannot modify its course."
                        )
                    )

        super().clean()

    def delete(self, using=None):
        """
        We need to synchronize with webhooks upon deletion. We could have used the signal but it
        also triggers on query deletes and is being called as many times as there are objects in
        the query. This would generate many separate calls to the webhook and would not scale. We
        decided to not provide synchronization for the moment on bulk deletes and leave it up to
        the developer to handle these cases correctly.
        """
        # Course run will be deleted, we synchronize it setting its visibility to hidden
        serialized_course_runs = [self.get_serialized(visibility=enums.HIDDEN)]

        super().delete(using=using)

        # Now synchronize the related products by recomputing the equivalent serialized course run
        serialized_course_runs.extend(
            self.get_equivalent_serialized_course_runs_for_related_products()
        )
        webhooks.synchronize_course_runs(serialized_course_runs)
