"""Context processors for the contract definition template."""

import io
from http import HTTPStatus
from logging import getLogger

from django.conf import settings

import html5lib
import requests
from pyRdfa import pyRdfa
from rdflib.namespace import RDF, SDO
from urllib3.util import Retry

logger = getLogger(__name__)

RETRY_STATUSES = [
    HTTPStatus.INTERNAL_SERVER_ERROR,
    HTTPStatus.BAD_GATEWAY,
    HTTPStatus.SERVICE_UNAVAILABLE,
    HTTPStatus.GATEWAY_TIMEOUT,
]

adapter = requests.adapters.HTTPAdapter(
    max_retries=Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=RETRY_STATUSES,
        allowed_methods=["GET"],
    )
)

session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)

RDFA_PROCESSOR = pyRdfa()
DOM_PARSER = html5lib.HTMLParser(tree=html5lib.getTreeBuilder("dom"))


def parse_richie_syllabus(course_code: str, language_code: str | None) -> dict:
    """
    If a remote Richie instance is configured, retrieve the syllabus
    through the provided `course_code` in the `language_code`
    otherwise it returns an empty dict.
    """
    url = settings.JOANIE_CATALOG_BASE_URL

    if not url:
        raise ValueError(
            "The origin of the Richie instance should "
            "be set through `JOANIE_CATALOG_BASE_URL` setting."
        )

    try:
        response = session.get(
            f"{url}/redirects/courses/{course_code}/",
            headers={"Accept-Language": language_code},
            timeout=10,
        )
    except requests.exceptions.RetryError as exception:
        logger.error(
            "Cannot fetch the Richie syllabus due to max retries exceeded.",
            exc_info=exception,
            extra={
                "context": {"course_code": course_code, "language_code": language_code}
            },
        )
        response = None
    except requests.exceptions.RequestException as exception:
        logger.error(
            "Cannot fetch the Richie syllabus: %s.",
            exception,
            exc_info=exception,
            extra={
                "context": {"course_code": course_code, "language_code": language_code}
            },
        )
        response = None
    else:
        if response.status_code != HTTPStatus.OK:
            logger.error(
                "Cannot fetch the Richie syllabus: %s.",
                response.status_code,
                extra={
                    "context": {
                        "course_code": course_code,
                        "language_code": language_code,
                    },
                    "response": response,
                },
            )
            response = None

    if response is None:
        return {}

    def get_object_repr(subject, predicate):
        """
        Retrieve the string representation of the first object
        matching the given `subject` and `predicate`.
        """
        return str(next(graph.objects(subject, predicate), ""))

    content = response.content.decode("utf-8")
    dom = DOM_PARSER.parse(io.StringIO(content))
    graph = RDFA_PROCESSOR.graph_from_DOM(dom)
    course = next(graph.subjects(predicate=RDF.type, object=SDO.Course), None)

    course_plans = graph.objects(course, SDO.syllabusSections)

    def build_course_plan(subject):
        """Recursively build the course plan of a Syllabus subject."""
        return {
            "name": get_object_repr(subject, SDO.name),
            "position": get_object_repr(subject, SDO.position),
            "children": [
                build_course_plan(part) for part in graph.objects(subject, SDO.hasPart)
            ],
        }

    context = {
        "title": get_object_repr(subject=course, predicate=SDO.name),
        "reference": get_object_repr(subject=course, predicate=SDO.courseCode),
        "cover": get_object_repr(subject=course, predicate=SDO.image),
        "abstract": get_object_repr(subject=course, predicate=SDO.abstract),
        "effort": get_object_repr(subject=course, predicate=SDO.timeRequired),
        "languages": get_object_repr(subject=course, predicate=SDO.availableLanguage),
        "categories": [
            get_object_repr(subject=c, predicate=SDO.name)
            for c in graph.objects(subject=course, predicate=SDO.keywords)
        ],
        "organizations": [
            {
                "name": get_object_repr(subject=o, predicate=SDO.name),
                "logo": get_object_repr(subject=o, predicate=SDO.logo),
                "url": get_object_repr(subject=o, predicate=SDO.url),
            }
            for o in graph.objects(subject=course, predicate=SDO.author)
        ],
        "team": [
            {
                "avatar": get_object_repr(subject=p, predicate=SDO.image),
                "name": get_object_repr(subject=p, predicate=SDO.name),
                "description": get_object_repr(subject=p, predicate=SDO.description),
                "url": get_object_repr(subject=p, predicate=SDO.url),
            }
            for p in graph.objects(subject=course, predicate=SDO.contributor)
        ],
        "description": get_object_repr(subject=course, predicate=SDO.description),
        "prerequisites": get_object_repr(
            subject=course, predicate=SDO.coursePrerequisites
        ),
        "abouts": [
            {
                "name": get_object_repr(about_subject, SDO.name),
                "description": get_object_repr(about_subject, SDO.description),
            }
            for about_subject in graph.objects(subject=course, predicate=SDO.about)
        ],
        "assessments": get_object_repr(
            subject=course, predicate=SDO.educationalCredentialAwarded
        ),
        "accessibility": get_object_repr(
            subject=course, predicate=SDO.accessibilitySummary
        ),
        "licenses": [
            {
                "logo": get_object_repr(subject=l, predicate=SDO.thumbnailUrl),
                "name": get_object_repr(subject=l, predicate=SDO.name),
                "description": get_object_repr(subject=l, predicate=SDO.abstract),
                "url": get_object_repr(subject=l, predicate=SDO.url),
            }
            for l in graph.objects(subject=course, predicate=SDO.license)
        ],
        "plan": [
            {
                "name": get_object_repr(course_plan, SDO.name),
                "parts": [
                    build_course_plan(part)
                    for part in graph.objects(course_plan, SDO.hasPart)
                ],
            }
            for course_plan in course_plans
        ],
    }

    return context
