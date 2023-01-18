"""
Models for the administration, legal and consulting&projects teams
"""
import hashlib
from os.path import splitext

from django.db import models
from django.utils.translation import gettext_lazy as _

from ..core.models import BaseModel


def contract_upload_to(instance, filename):
    _, ext = splitext(filename)
    ctx = hashlib.sha256()
    ctx.update(instance.file.read())
    file_hash = ctx.hexdigest()
    return 'organization/{instance.organization.id}/contracts/{file_hash}.{file_ext}'


class Contract(BaseModel):
    start = models.DateField(vebose_name=_('start of the contract'))
    end = models.DateField(verbose_name=_('end of the contract'), null=True, default=None, blank=True)
    file = models.FileField(verbose_name=_('file of the signed contract'), upload_to=contract_upload_to)
    organization = models.ForeignKey(
        Organization,
        verbose_name=_('organization'),
        help_text=_('the organization signing the contract'),
        on_delete=models.PROTECT,
)
        


class PreCourse(BaseModel):
    # submission time
    # titre du cours
    # status du cours
    # session
    # diffusion
    # date de début des inscriptions
    # date de début du cours
    # date de fin du cours
    # date de fin des inscriptions
    # chef de projet
    # type de cours
    #MOOC = 'MOOC'
    #SPOCA = 'SPOCA'
    #SPOCC = 'SPOCC'
    #KIND_CHOICES = [
    #    (MOOC, _("MOOC")),
    #    (SPOCA, _("Academic SPOC")),
    #    (SPOCC, _("Corporate SPOC")),
    #]
    #kind = models.CharField(
    #    max_length=5,
    #    choices=KIND_CHOICES,
    #    default=None,
    #    null=True,
    #)
    # estimation du nombre d'apprenant·e·s
    # etablissement adherent
    # etablissement porteur
    # etablissement producteur
    # double affichage
    # etablissement secondaire
    # description courte
    # contact mooc
    # mail
    # telephone
    # thématiques
    # durée en semaines de cours
    # temps de travails hebdomadaire estimé
    # commentaires
    # attestation ou badge
    # enseignants pour l'attestation
    # date prévisionnelle de génération
    # type de certificat
    # date de début de l'examen
    # date de fin de l'examen
    # date d'ouverture du paiement
    # date de fin du paiement
    # prix de l'examen
    # date de génération des certificats


class ContractConsumption(BaseModel):
    contract = models.ForeignKey(
        Contract,
        verbose_name=_('contract'),
        related_name='consumptions'),
        on_delete=models.CASCADE,
    )
    debit = models.PositivIntegerField(
        verbose_name=_('Debit'),
    )
    credit = models.PositiveIntegerField(verbose_name=_('Credit'))
    source = models.ForeignKey(PreCourse, verbose_name='source of debit', on_delete=models.PROTECT)
