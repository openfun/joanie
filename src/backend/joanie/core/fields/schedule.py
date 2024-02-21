"""Utils for the order payment schedule field"""

from django.core.serializers.json import DjangoJSONEncoder

from stockholm import Money


class OrderPaymentScheduleEncoder(DjangoJSONEncoder):
    """
    A JSON encoder for datetime objects.
    """

    def default(self, o):
        if isinstance(o, Money):
            return o.amount_as_string()

        return super().default(o)
