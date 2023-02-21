"""
Utils that can be useful throughout Joanie's core app to synchronize data with other services
"""
import hashlib
import hmac
import json
import logging

from django.conf import settings

import requests
from urllib3.util import Retry

logger = logging.getLogger(__name__)

adapter = requests.adapters.HTTPAdapter(
    max_retries=Retry(
        total=4,
        backoff_factor=0.1,
        status_forcelist=[500],
        allowed_methods=["POST"],
    )
)

session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)


def synchronize_course_runs(serialized_course_runs):
    """webhook to synchronize data"""
    if not settings.COURSE_WEB_HOOKS or not serialized_course_runs:
        return

    json_course_runs = json.dumps(serialized_course_runs).encode("utf-8")
    for webhook in settings.COURSE_WEB_HOOKS:
        signature = hmac.new(
            str(webhook["secret"]).encode("utf-8"),
            msg=json_course_runs,
            digestmod=hashlib.sha256,
        ).hexdigest()

        try:
            response = session.post(
                webhook["url"],
                json=serialized_course_runs,
                headers={"Authorization": f"SIG-HMAC-SHA256 {signature:s}"},
                verify=bool(webhook.get("verify", True)),
                timeout=3,
            )

        except requests.exceptions.RetryError:
            logger.error(
                "Synchronization failed due to max retries exceeded with url %s",
                webhook["url"],
            )
        else:
            extra = {
                "sent": json_course_runs,
                "response": response.content,
            }
            # pylint: disable=no-member
            if response.status_code == requests.codes.ok:
                logger.info(
                    "Synchronization succeeded with %s",
                    webhook["url"],
                    extra=extra,
                )
            else:
                logger.error(
                    "Synchronization failed with %s",
                    webhook["url"],
                    extra=extra,
                )
