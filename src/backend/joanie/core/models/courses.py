"""
Declare and configure the models for the courses part
"""
from collections.abc import Mapping
from datetime import MAXYEAR, datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.functional import lazy
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

import pytz
from parler import models as parler_models
from url_normalize import url_normalize

from joanie.core import utils
from joanie.core.enums import ALL_LANGUAGES
from joanie.core.fields.multiselect import MultiSelectField

MAX_DATE = datetime(MAXYEAR, 12, 31, tzinfo=pytz.utc)


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
        self._d = dict(**kwargs)

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


class Organization(parler_models.TranslatableModel):
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
    logo = models.ImageField(_("logo"), blank=True)

    class Meta:
        db_table = "joanie_organization"
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")

    def __str__(self):
        return (
            f"[{self.code}] {self.safe_translation_getter('title', any_language=True)}"
        )


class Course(parler_models.TranslatableModel):
    """
    Course model represents and records a course in the cms catalog.
    A new course created will initialize a cms page.
    """

    code = models.CharField(_("code"), max_length=100, unique=True, db_index=True)
    translations = parler_models.TranslatedFields(
        title=models.CharField(_("title"), max_length=255)
    )
    organization = models.ForeignKey(
        Organization,
        verbose_name=_("organization"),
        on_delete=models.PROTECT,
    )
    products = models.ManyToManyField(
        "Product",
        related_name="courses",
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

    def get_cache_key(self, language=None):
        """
        Return a course cache key related to its code and the current
        language can be forced by through the language argument.
        """
        current_language = language or get_language()
        return f"course-{self.code}-{current_language}"

    def clean(self):
        """
        We normalize the code with slugify for better uniqueness
        """
        # Normalize the code by slugifying and capitalizing it
        self.code = utils.normalize_code(self.code)
        return super().clean()

    def save(self, *args, **kwargs):
        """
        Enforce validation each time an instance is saved
        """
        self.full_clean()
        super().save(*args, **kwargs)


class CourseRun(parler_models.TranslatableModel):
    """
    Course run represents and records the occurrence of a course between a start
    and an end date.
    """

    course = models.ForeignKey(
        Course,
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
        choices=lazy(lambda: ALL_LANGUAGES, tuple)(),
        help_text=_("The list of languages in which the course content is available."),
    )

    class Meta:
        db_table = "joanie_course_run"
        verbose_name = _("Course run")
        verbose_name_plural = _("Course runs")

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

        now = timezone.now()
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

    def __str__(self):
        return (
            f"{self.safe_translation_getter('title', any_language=True)} "
            f"[{self.start:%Y-%m-%d} to {self.end:%Y-%m-%d}]"
        )

    def clean(self):
        """Normalize the resource_link url."""
        self.resource_link = url_normalize(self.resource_link)
        super().clean()

    def save(self, *args, **kwargs):
        """Call full clean before saving instance."""
        self.full_clean()
        super().save(*args, **kwargs)
