import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";

export type Discount = {
  id: string;
  amount: number | null;
  rate: number | null;
};

export type DTODiscount = Omit<Discount, "id">;

export type DiscountQuery = ResourcesQuery & {};

export const getDiscountLabel = (discount: Maybe<Discount>) => {
  if (!discount) {
    return "";
  }
  if (discount.rate) {
    return `${discount.rate * 100}%`;
  }
  if (discount.amount) {
    return `${discount.amount} €`;
  }
  return discount.id;
};
