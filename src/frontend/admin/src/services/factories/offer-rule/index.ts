import { faker } from "@faker-js/faker";
import { OfferRule } from "@/services/api/models/OfferRule";
import { DiscountFactory } from "@/services/factories/discounts";

const build = (): OfferRule => {
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

export function OfferRuleFactory(): OfferRule;
export function OfferRuleFactory(count: number): OfferRule[];
export function OfferRuleFactory(count?: number): OfferRule | OfferRule[] {
  if (count) return [...Array(count)].map(() => build());
  return build();
}
