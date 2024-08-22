import { faker } from "@faker-js/faker";
import { OrderCreditCard } from "@/services/api/models/Order";

const build = (override: Partial<OrderCreditCard> = {}): OrderCreditCard => ({
  id: faker.string.uuid(),
  last_numbers: faker.finance.creditCardNumber().slice(-4),
  brand: faker.helpers.arrayElement(["Visa", "Mastercard", "Maestro", "Amex"]),
  expiration_month: faker.date.future().getMonth() + 1,
  expiration_year: faker.date.future().getFullYear(),
  ...override,
});

export function CreditCardFactory(
  override?: Partial<OrderCreditCard>,
  args_1?: undefined,
): OrderCreditCard;
export function CreditCardFactory(
  count: number,
  override?: Partial<OrderCreditCard>,
): OrderCreditCard[];
export function CreditCardFactory(
  ...args: [
    number | Partial<OrderCreditCard> | undefined,
    Partial<OrderCreditCard> | undefined,
  ]
) {
  if (typeof args[0] === "number") {
    return [...Array(args[0])].map(() => build(args[1]));
  }
  return build(args[0]);
}
