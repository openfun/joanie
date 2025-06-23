import { faker } from "@faker-js/faker";
import { OfferingRule } from "@/services/api/models/OfferingRule";
import { DiscountFactory } from "@/services/factories/discounts";

const build = (): OfferingRule => {
  const nbSeat = faker.number.int({ max: 200 });
  return {
    id: faker.string.uuid(),
    description: faker.lorem.sentence({ min: 1, max: 3 }),
    nb_seats: nbSeat,
    nb_available_seats: faker.number.int({ max: nbSeat }),
    start: faker.date.recent().toISOString(),
    end: faker.date.future().toISOString(),
    is_active: faker.datatype.boolean(),
    can_edit: faker.datatype.boolean(),
    discount: DiscountFactory(),
  };
};

export function OfferingRuleFactory(): OfferingRule;
export function OfferingRuleFactory(count: number): OfferingRule[];
export function OfferingRuleFactory(
  count?: number,
): OfferingRule | OfferingRule[] {
  if (count) return [...Array(count)].map(() => build());
  return build();
}
