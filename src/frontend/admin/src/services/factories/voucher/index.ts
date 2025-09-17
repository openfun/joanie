import { faker } from "@faker-js/faker";
import { Voucher } from "@/services/api/models/Voucher";
import { DiscountFactory } from "@/services/factories/discounts";

function build(): Voucher {
  const hasDiscount = faker.datatype.boolean();

  return {
    id: faker.string.uuid(),
    code: faker.string.alphanumeric(10).toUpperCase(),
    discount: hasDiscount ? DiscountFactory() : null,
    multiple_use: faker.datatype.boolean(),
    multiple_users: faker.datatype.boolean(),
  };
}

export function VoucherFactory(): Voucher;
export function VoucherFactory(count: number): Voucher[];
export function VoucherFactory(count?: number): Voucher | Voucher[] {
  if (count) return [...Array(count)].map(build);
  return build();
}
