"""Test suite for the contract context processors utilities."""

import random
from http import HTTPStatus
from logging import Logger
from unittest import mock

from django.test import TestCase, override_settings

import requests
import responses

from joanie.core.utils.contract_context_processors import (
    RETRY_STATUSES,
    parse_richie_syllabus,
)


class UtilsContractContextProcessors(TestCase):
    """Test suite for the contract context processors utilities."""

    maxDiff = None

    @override_settings(JOANIE_CATALOG_BASE_URL="http://richie.test")
    def test_contract_context_processors_parse_richie_syllabus(self):
        """
        `parse_richie_syllabus` should return a dict a property "syllabus" containing all the
        attributes of the syllabus extracted from the remote Richie instance through
        RDF attributes.
        """
        with responses.RequestsMock() as m:
            mock_request = m.get(
                "http://richie.test/redirects/courses/178001/",
                status=HTTPStatus.OK,
                body="""
                <body vocab="https://schema.org/" typeof="Course">
                    <h1 property="name">Course title</h1>
                    <img src="//fun-cdn.net/images/1" property="image" />
                    <span property="courseCode">178001</span>
                    <span property="timeRequired">PT3H</span>
                    <span property="availableLanguage">French</span>
                    <ul>
                        <li property="keywords" typeof="DefinedTerm">
                            <span property="name">Category 1</span>
                        </li>
                        <li property="keywords" typeof="DefinedTerm">
                            <span property="name">Category 2</span>
                        </li>
                    </ul>
                    <p property="abstract">Course short description</p>
                    <p property="description">Course long description</p>
                    <p property="coursePrerequisites">Course prerequisites</p>
                    <p property="educationalCredentialAwarded">Course assessments and awards</p>
                    <p property="accessibilitySummary">What is the accessibility of this course?</p>
                    <div property="about" typeof="Thing">
                        <h2 property="name">Format</h2>
                        <p property="description">Course format</p>
                    </div>
                    <div property="about" typeof="Thing">
                        <h2 property="name">What you will learn?</h2>
                        <p property="description">Course teaches</p>
                    </div>
                    <div property="about" typeof="Thing">
                        <h2 property="name">Required Equipment</h2>
                        <p property="description">What are the required equipment to follow this course?</p>
                    </div>
                    <div property="author" typeof="Organization">
                        <img src="//fun-cdn.net/images/2" property="logo" />
                        <span property="name">Organization name</span>
                        <meta property="url" content="http://richie.test/en/orgs/1" />
                    </div>
                    <div property="contributor" typeof="Person">
                        <img src="//fun-cdn.net/images/3" property="image" />
                        <span property="name">Contributor name</span>
                        <span property="description">Contributor bio</span>
                        <meta property="url" content="http://richie.test/en/person/1" />
                    </div>
                    <div property="license" typeof="CreativeWork">
                        <img src="//fun-cdn.net/images/4" property="thumbnailUrl" />
                        <span property="name">CC BY-NC-ND 4.0</span>
                        <span property="abstract">License description</span>
                        <meta property="url" content="https://creativecommons.org/licenses/by-nc-nd/4.0/deed.fr" />
                    </div>
                    <ul property="syllabusSections" typeof="Syllabus">
                        <li property="hasPart" typeof="Syllabus">
                            <h3 property="name">Chapter 1</h3>
                            <meta property="position" content="0" />
                            <ul>
                                <li property="hasPart" typeof="Syllabus">
                                    <h4 property="name">Part 1</h4>
                                    <meta property="position" content="0" />
                                </li>
                                <li property="hasPart" typeof="Syllabus">
                                    <h4 property="name">Part 2</h4>
                                    <meta property="position" content="1" />
                                </li>
                            </ul>
                        </li>
                        <li property="hasPart" typeof="Syllabus">
                            <h3 property="name">Chapter 2</h3>
                            <meta property="position" content="1" />
                        </li>
                    </ul>
                </body>
                """,
            )
            context = parse_richie_syllabus("178001", "fr-fr")

        self.assertEqual(mock_request.call_count, 1)
        self.assertEqual(
            mock_request.calls[0].request.headers["Accept-Language"], "fr-fr"
        )

        self.assertEqual(context["title"], "Course title")
        self.assertEqual(context["reference"], "178001")
        self.assertEqual(context["cover"], "//fun-cdn.net/images/1")
        self.assertEqual(context["abstract"], "Course short description")
        self.assertEqual(context["description"], "Course long description")
        self.assertEqual(context["prerequisites"], "Course prerequisites")
        self.assertEqual(context["assessments"], "Course assessments and awards")
        self.assertEqual(
            context["accessibility"], "What is the accessibility of this course?"
        )
        self.assertEqual(context["effort"], "PT3H")
        self.assertEqual(context["languages"], "French")
        self.assertCountEqual(context["categories"], ["Category 1", "Category 2"])
        self.assertCountEqual(
            context["abouts"],
            [
                {
                    "name": "Format",
                    "description": "Course format",
                },
                {
                    "name": "What you will learn?",
                    "description": "Course teaches",
                },
                {
                    "name": "Required Equipment",
                    "description": "What are the required equipment to follow this course?",
                },
            ],
        )
        self.assertEqual(
            context["organizations"],
            [
                {
                    "logo": "//fun-cdn.net/images/2",
                    "name": "Organization name",
                    "url": "http://richie.test/en/orgs/1",
                }
            ],
        )
        self.assertEqual(
            context["team"],
            [
                {
                    "avatar": "//fun-cdn.net/images/3",
                    "name": "Contributor name",
                    "description": "Contributor bio",
                    "url": "http://richie.test/en/person/1",
                }
            ],
        )
        self.assertEqual(
            context["licenses"],
            [
                {
                    "logo": "//fun-cdn.net/images/4",
                    "name": "CC BY-NC-ND 4.0",
                    "description": "License description",
                    "url": "https://creativecommons.org/licenses/by-nc-nd/4.0/deed.fr",
                }
            ],
        )

        course_plan = context["plan"]
        self.assertEqual(len(course_plan), 1)
        course_plan = course_plan[0]
        self.assertEqual(course_plan["name"], "")
        self.assertEqual(len(course_plan["parts"]), 2)
        chapter_1 = next(
            (x for x in course_plan["parts"] if x["name"] == "Chapter 1"), None
        )
        self.assertEqual(chapter_1["position"], "0")
        self.assertEqual(len(chapter_1["children"]), 2)
        part_1 = next((x for x in chapter_1["children"] if x["name"] == "Part 1"), None)
        part_2 = next((x for x in chapter_1["children"] if x["name"] == "Part 2"), None)
        self.assertEqual(part_1["position"], "0")
        self.assertEqual(part_1["children"], [])
        self.assertEqual(part_2["position"], "1")
        self.assertEqual(part_2["children"], [])

        chapter_2 = next(
            (x for x in course_plan["parts"] if x["name"] == "Chapter 2"), None
        )
        self.assertEqual(chapter_2["position"], "1")
        self.assertEqual(chapter_2["children"], [])

    @override_settings(JOANIE_CATALOG_BASE_URL="http://richie.test")
    def test_contract_context_processors_parse_richie_syllabus_empty_values(self):
        """
        `parse_richie_syllabus` should return a dict a property "syllabus" containing all the
        attributes of the syllabus extracted from the remote Richie instance through
        RDF attributes. If an attributes is not found, it should be set with an empty value.
        """
        with responses.RequestsMock() as m:
            mock_request = m.get(
                "http://richie.test/redirects/courses/178001/",
                status=HTTPStatus.OK,
            )
            context = parse_richie_syllabus("178001", "en-us")

        self.assertEqual(mock_request.call_count, 1)
        self.assertEqual(
            mock_request.calls[0].request.headers["Accept-Language"], "en-us"
        )

        self.assertEqual(
            context,
            {
                "title": "",
                "reference": "",
                "cover": "",
                "abstract": "",
                "description": "",
                "prerequisites": "",
                "assessments": "",
                "accessibility": "",
                "effort": "",
                "languages": "",
                "categories": [],
                "abouts": [],
                "organizations": [],
                "team": [],
                "licenses": [],
                "plan": [],
            },
        )

    @override_settings(JOANIE_CATALOG_BASE_URL=None)
    def test_contract_context_processors_parse_richie_syllabus_missing_setting(self):
        """
        When the `parse_richie_syllabus_request` is called without JOANIE_CATALOG_BASE_URL
        set a ValueError should be raised.
        """

        with self.assertRaises(ValueError) as context:
            parse_richie_syllabus("178001", "en-us")

        self.assertEqual(
            str(context.exception),
            "The origin of the Richie instance should "
            "be set through `JOANIE_CATALOG_BASE_URL` setting.",
        )

    @override_settings(JOANIE_CATALOG_BASE_URL="http://richie.test")
    @mock.patch.object(Logger, "error")
    def test_contract_context_processors_parse_richie_syllabus_request_failure(
        self, mock_logger
    ):
        """
        When the request to the remote Richie instance fails,
        an empty dict should be returned and an error should be logged.
        """
        with responses.RequestsMock() as m:
            mock_request = m.get(
                "http://richie.test/redirects/courses/178001/",
                status=HTTPStatus.NOT_FOUND,
            )
            context = parse_richie_syllabus("178001", "fr-fr")

        self.assertEqual(mock_request.call_count, 1)

        # - The logger should have been called once with details about the error
        self.assertEqual(mock_logger.call_count, 1)
        self.assertEqual(
            mock_logger.call_args_list[0][0],
            ("Cannot fetch the Richie syllabus: %s.", HTTPStatus.NOT_FOUND),
        )
        self.assertEqual(
            mock_logger.call_args_list[0][1]["extra"]["context"],
            {"course_code": "178001", "language_code": "fr-fr"},
        )
        self.assertIsInstance(
            mock_logger.call_args_list[0][1]["extra"]["response"],
            requests.Response,
        )

        # - The context should be an empty dict
        self.assertEqual(context, {})

    @override_settings(JOANIE_CATALOG_BASE_URL="http://richie.test")
    @mock.patch.object(Logger, "error")
    def test_contract_context_processors_parse_richie_syllabus_request_failure_max_retries(
        self, mock_logger
    ):
        """
        When the request to the remote Richie instance fails with 5xx errors,
        the request should be retried 3 times afterward an empty dict should be returned
        and an error should be logged.
        """
        with responses.RequestsMock() as m:
            mock_request = m.get(
                "http://richie.test/redirects/courses/178001/",
                status=random.choice(RETRY_STATUSES),
            )
            context = parse_richie_syllabus("178001", "en-us")

        # - The request should be retried 3 times
        self.assertEqual(mock_request.call_count, 4)

        # - The logger should have been called once with details about the error
        self.assertEqual(mock_logger.call_count, 1)
        self.assertEqual(
            mock_logger.call_args_list[0][0],
            ("Cannot fetch the Richie syllabus due to max retries exceeded.",),
        )
        self.assertEqual(
            mock_logger.call_args_list[0][1]["extra"],
            {
                "context": {
                    "course_code": "178001",
                    "language_code": "en-us",
                }
            },
        )
        self.assertIsInstance(
            mock_logger.call_args_list[0][1]["exc_info"],
            requests.exceptions.RetryError,
        )

        # - The context should be an empty dict
        self.assertEqual(context, {})
