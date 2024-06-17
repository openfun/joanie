"""Module for certificate filters."""

from typing import List

from django.db.models import Q

from django_filters import rest_framework as filters

from joanie.core import enums, models


class CertificateViewSetFilter(filters.FilterSet):
    """
    Filter certificates by enrollment or order
    """

    def __init__(self, *args, **kwargs):
        """Use initial values as defaults for bound filterset."""
        super().__init__(*args, **kwargs)
        # if filterset is bound, use initial values as defaults
        if self.data is not None:
            # get a mutable copy of the QueryDict
            data = self.data.copy()

            for name, f in self.filters.items():
                initial = f.extra.get("initial")

                # filter param is either missing or empty, use initial as default
                if not data.get(name) and initial:
                    data[name] = initial

            self.data = data

    type = filters.ChoiceFilter(
        choices=enums.CERTIFICATE_TYPE_CHOICES,
        method="filter_by_type",
        initial=enums.CERTIFICATE_ORDER_TYPE,
    )

    class Meta:
        model = models.Certificate
        fields: List[str] = []

    def filter_by_type(self, queryset, _name, value):
        """
        Filter certificates by type
        """
        username = (
            self.request.auth["username"]
            if self.request.auth
            else self.request.user.username
        )
        if value == enums.CERTIFICATE_ORDER_TYPE:
            # Retrieve all certificates that belong to orders of the user
            # and also legacy degrees linked to an enrollment
            return queryset.filter(
                Q(order__owner__username=username)
                | (
                    Q(enrollment__user__username=username)
                    & Q(certificate_definition__template=enums.DEGREE)
                )
            )

        if value == enums.CERTIFICATE_ENROLLMENT_TYPE:
            return queryset.filter(
                enrollment__user__username=username,
                certificate_definition__template=enums.CERTIFICATE,
            )

        return queryset.none()
