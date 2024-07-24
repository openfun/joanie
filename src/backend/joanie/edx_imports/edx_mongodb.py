"""Module to connect to Open edX mongodb and extract data"""

from django.conf import settings

from pymongo import MongoClient

from joanie.lms_handler.backends.openedx import split_course_key


def get_signatory_from_course_id(course_id):
    """Get signatory from course id"""
    client = MongoClient(
        host=settings.EDX_MONGODB_HOST,
        port=settings.EDX_MONGODB_PORT,
        username=settings.EDX_MONGODB_USER,
        password=settings.EDX_MONGODB_PASSWORD,
        authSource=settings.EDX_MONGODB_NAME,
        readPreference=settings.EDX_MONGODB_READPREFERENCE,
        replicaSet=settings.EDX_MONGODB_REPLICASET,
    )
    db = client.edxapp
    (org, course, run) = split_course_key(course_id)
    mongo_course = db.modulestore.active_versions.find_one(
        {
            "org": org,
            "course": course,
            "run": run,
        },
        {"versions.published-branch": 1},
    )

    try:
        structure_id = mongo_course.get("versions").get("published-branch")
    except (AttributeError, IndexError):
        return None

    structure = db.modulestore.structures.find_one(
        {"_id": structure_id},
        {
            "blocks": {"$elemMatch": {"block_type": "course"}},
            "blocks.fields.certificates.certificates.signatories": 1,
        },
    )

    try:
        signatory = (
            structure.get("blocks")[0]
            .get("fields")
            .get("certificates")
            .get("certificates")[0]
            .get("signatories")[0]
        )
    except (AttributeError, IndexError):
        signatory = None

    return signatory
