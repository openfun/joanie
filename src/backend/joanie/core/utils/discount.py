"""Utils for discount calculation."""

from stockholm import Money, Number, Rate


def calculate_price(price, discount):
    """
    Calculate the discounted price.
    """
    price = Money(price)
    discount_amount = (
        Money(discount.amount)
        if discount.amount
        else price * Rate(Number(discount.rate))
    )
    return round(Money(price - discount_amount).as_decimal(), 2)
