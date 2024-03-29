"""Module to connect to Open edX mongodb and extract data"""

from django.conf import settings

from pymongo import MongoClient


def get_signature_from_enrollment(course_id):
    """Get signature from mongodb enrollment"""
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
    mongo_enrollment = db.modulestore.find_one(
        {"_id.course": course_id, "_id.category": "course"},
        {"metadata.certificates": 1},
    )

    try:
        signatory = (
            mongo_enrollment.get("metadata")
            .get("certificates")
            .get("certificates")[0]
            .get("signatories")[0]
        )
    except (AttributeError, IndexError):
        signatory = None

    return signatory
