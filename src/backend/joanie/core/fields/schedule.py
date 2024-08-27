"""Utils for the order payment schedule field"""

from datetime import date
from json import JSONDecoder
from json.decoder import WHITESPACE

from django.core.serializers.json import DjangoJSONEncoder

from stockholm import Money


class OrderPaymentScheduleEncoder(DjangoJSONEncoder):
    """
    A JSON encoder for order payment schedule objects.
    """

    def default(self, o):
        if isinstance(o, Money):
            return o.amount_as_string()

        return super().default(o)


class OrderPaymentScheduleDecoder(JSONDecoder):
    """
    A JSON decoder for order payment schedule objects.
    """

    def decode(self, s, _w=WHITESPACE.match):
        payment_schedule = super().decode(s, _w)
        for installment in payment_schedule:
            installment["amount"] = Money(installment["amount"])
            installment["due_date"] = date.fromisoformat(installment["due_date"])
        return payment_schedule
