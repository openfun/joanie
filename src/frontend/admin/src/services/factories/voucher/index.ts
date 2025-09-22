import { faker } from "@faker-js/faker";
import { Voucher } from "@/services/api/models/Voucher";
import { DiscountFactory } from "@/services/factories/discounts";

function build(): Voucher {
  return {
    id: faker.string.uuid(),
    code: faker.string.alphanumeric(10).toUpperCase(),
    discount: DiscountFactory(),
    is_active: faker.datatype.boolean(),
    multiple_use: faker.datatype.boolean(),
    multiple_users: faker.datatype.boolean(),
    orders_count: faker.number.int({ min: 0, max: 100 }),
  };
}

export function VoucherFactory(): Voucher;
export function VoucherFactory(count: number): Voucher[];
export function VoucherFactory(count?: number): Voucher | Voucher[] {
  if (count) return [...Array(count)].map(build);
  return build();
}
