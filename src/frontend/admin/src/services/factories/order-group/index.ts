import { faker } from "@faker-js/faker";
import { OrderGroup } from "@/services/api/models/OrderGroup";

const build = (): OrderGroup => {
  const nbSeat = faker.number.int({ max: 200 });
  return {
    id: faker.string.uuid(),
    nb_seats: nbSeat,
    nb_available_seats: faker.number.int({ max: nbSeat }),
    is_active: faker.datatype.boolean(),
    can_edit: faker.datatype.boolean(),
  };
};

export function OrderGroupFactory(): OrderGroup;
export function OrderGroupFactory(count: number): OrderGroup[];
export function OrderGroupFactory(count?: number): OrderGroup | OrderGroup[] {
  if (count) return [...Array(count)].map(() => build());
  return build();
}
