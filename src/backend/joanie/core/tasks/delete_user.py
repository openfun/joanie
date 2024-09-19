"""Celery task to delete a user."""

from logging import getLogger

from django.contrib.auth import get_user_model

from joanie.celery_app import app

logger = getLogger(__name__)


@app.task
def delete_user(username):
    """Delete a user by username."""
    user_model = get_user_model()
    try:
        user = user_model.objects.get(username=username)
    except user_model.DoesNotExist:
        logger.warning("User %s does not exist.", username)
        return

    user.delete()

    logger.info("User %s has been deleted.", username)
