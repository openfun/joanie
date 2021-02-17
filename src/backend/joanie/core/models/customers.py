from django.db import models

from django.utils.translation import gettext_lazy as _


class User(models.Model):
    username = models.CharField(_("username"), max_length=255, unique=True)
    payment_token = models.CharField(_("payment token"), max_length=255, blank=True)

    class Meta:
        db_table = "joanie_user"
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def __str__(self):
        return self.username
