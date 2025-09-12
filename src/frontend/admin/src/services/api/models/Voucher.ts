import { Discount } from "@/services/api/models/Discount";
import { ResourcesQuery } from "@/hooks/useResources";

export type Voucher = {
  id: string;
  code: string;
  discount: Discount | null;
  multiple_use: boolean;
  multiple_users: boolean;
};

export type DTOVoucher = {
  code?: string;
  discount_id?: Discount["id"] | null;
  multiple_use: Voucher["multiple_use"];
  multiple_users: Voucher["multiple_users"];
};

export type VoucherQuery = ResourcesQuery & {};
