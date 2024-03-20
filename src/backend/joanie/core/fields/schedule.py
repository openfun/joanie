"""Utils for the order payment schedule field"""

import datetime
from json import JSONEncoder

from stockholm import Money


class OrderPaymentScheduleEncoder(JSONEncoder):
    """
    A JSON encoder for datetime objects.
    """

    def default(self, o):
        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()

        if isinstance(o, Money):
            return o.amount_as_string()

        return super().default(o)
