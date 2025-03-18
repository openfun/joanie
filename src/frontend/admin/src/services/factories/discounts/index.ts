import { faker } from "@faker-js/faker";
import { Discount } from "@/services/api/models/Discount";

function build(): Discount {
  const useAmount = faker.datatype.boolean();

  return {
    id: faker.string.uuid(),
    amount: useAmount ? faker.number.int({ min: 1, max: 100 }) : null,
    rate: !useAmount
      ? faker.number.float({ min: 0.01, max: 1, fractionDigits: 2 })
      : null,
  };
}

export function DiscountFactory(): Discount;
export function DiscountFactory(count: number): Discount[];
export function DiscountFactory(count?: number): Discount | Discount[] {
  if (count) return [...Array(count)].map(build);
  return build();
}
