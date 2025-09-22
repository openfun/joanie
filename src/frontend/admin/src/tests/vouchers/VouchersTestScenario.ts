import { Voucher } from "@/services/api/models/Voucher";
import { VoucherFactory } from "@/services/factories/voucher";
import { Discount } from "@/services/api/models/Discount";
import { DiscountFactory } from "@/services/factories/discounts";

export const getVouchersScenarioStore = (itemsNumber: number = 10) => {
  const list: Voucher[] = VoucherFactory(itemsNumber) as Voucher[];
  const discounts: Discount[] = DiscountFactory(3);

  return {
    list,
    discounts,
  };
};
