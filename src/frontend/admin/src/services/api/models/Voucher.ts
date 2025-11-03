import { Discount } from "@/services/api/models/Discount";
import { ResourcesQuery } from "@/hooks/useResources";

export type Voucher = {
  id: string;
  code: string;
  discount: Discount | null;
  multiple_use: boolean;
  multiple_users: boolean;
  orders_count: number;
  is_active: boolean;
};

export type DTOVoucher = {
  id?: Voucher["id"];
  code?: Voucher["code"] | null;
  discount_id?: Discount["id"] | null;
  multiple_use: Voucher["multiple_use"];
  multiple_users: Voucher["multiple_users"];
  is_active: Voucher["is_active"];
};

export type VoucherQuery = ResourcesQuery & {};
