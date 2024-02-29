# pylint: disable=broad-except
# ruff: noqa: BLE001
"""
Check the environment variables and database connections required for the import tasks.
"""

from http import HTTPStatus
from logging import getLogger

from django.conf import settings

import requests
from pymongo import MongoClient

from joanie.edx_imports.edx_database import OpenEdxDB

logger = getLogger(__name__)


def check_import_env(style):
    """
    Check the environment variables required for the import tasks.
    """
    logger.info("\n- Checking import environment variables...")

    check_result = True
    for env_var in [
        "EDX_DATABASE_HOST",
        "EDX_DOMAIN",
        "EDX_DATABASE_NAME",
        "EDX_DATABASE_USER",
        "EDX_DATABASE_PASSWORD",
        "EDX_DATABASE_DEBUG",
        "EDX_TIME_ZONE",
        "EDX_SECRET",
        "EDX_MONGODB_HOST",
        "EDX_MONGODB_PORT",
        "EDX_MONGODB_USER",
        "EDX_MONGODB_PASSWORD",
        "EDX_MONGODB_NAME",
    ]:
        try:
            logger.info(
                style.SUCCESS("    %s: %s"), env_var, getattr(settings, env_var)
            )
        except AttributeError:
            logger.error(style.ERROR("    %s is not defined"), env_var)
            check_result = False
    return check_result


def check_course_sync_env(style):
    """
    Check that the environment variables for the course sync is empty.
    """
    logger.info("\n- Checking course sync environment variables...")

    env_var = "COURSE_WEB_HOOKS"
    try:
        course_web_hook_settings = getattr(settings, env_var)
        if course_web_hook_settings:
            logger.error(
                style.ERROR("    %s is defined: %s"), env_var, course_web_hook_settings
            )
            logger.error(
                style.ERROR("    Courses will be synced during the import process.")
            )
            return False
    except AttributeError:
        pass

    logger.info(style.SUCCESS("    No course sync environment variables defined"))
    return True


def check_openedx_host(style):
    """
    Check the Open edX host.
    """
    url = f"https://{settings.EDX_DOMAIN}/"
    logger.info("\n- Checking Open edX host %s...", url)

    try:
        response = requests.get(url, stream=True, timeout=3)
        if response.status_code == HTTPStatus.OK:
            logger.info(style.SUCCESS("    Open edX host is reachable"))
            return True
        logger.error(style.ERROR("    Open edX host is not reachable"))
    except Exception as e:
        logger.error(style.ERROR("    Open edX host is not reachable : "), e)
    return False


def check_import_db_connections(style):
    """
    Check the database connections required for the import tasks.
    """
    logger.info("\n- Checking import databases connections...")

    check_result = True
    try:
        logger.info("\n  Open edX postgres database...")
        db = OpenEdxDB()
        db.get_universities_count()
        logger.info(style.SUCCESS("    Open edX postgres database : OK"))
    except Exception as e:
        logger.error(style.ERROR("    Open edX postgres database : %s"), e)
        check_result = False

    try:
        logger.info("\n  Open edX mongodb database...")
        client = MongoClient(
            host=settings.EDX_MONGODB_HOST,
            port=settings.EDX_MONGODB_PORT,
            username=settings.EDX_MONGODB_USER,
            password=settings.EDX_MONGODB_PASSWORD,
            authSource=settings.EDX_MONGODB_NAME,
        )
        db = client.edxapp
        db.modulestore.find_one()
        logger.info(style.SUCCESS("    Open edX mongodb database : OK"))
    except Exception as e:
        logger.error(style.ERROR("    Open edX mongodb database : %s"), e)
        check_result = False

    return check_result
