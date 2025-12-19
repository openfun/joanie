import { ResourcesQuery } from "@/hooks/useResources";
import { Organization } from "@/services/api/models/Organization";
import { Nullable } from "@/types/utils";
import { User } from "@/services/api/models/User";
import { Offering } from "@/services/api/models/Offerings";
import { OrderListItem } from "@/services/api/models/Order";

export enum BatchOrderStatesEnum {
  BATCH_ORDER_STATE_DRAFT = "draft",
  BATCH_ORDER_STATE_ASSIGNED = "assigned",
  BATCH_ORDER_STATE_QUOTED = "quoted",
  BATCH_ORDER_STATE_TO_SIGN = "to_sign",
  BATCH_ORDER_STATE_SIGNING = "signing",
  BATCH_ORDER_STATE_PENDING = "pending",
  BATCH_ORDER_STATE_PROCESS_PAYMENT = "process_payment",
  BATCH_ORDER_STATE_FAILED_PAYMENT = "failed_payment",
  BATCH_ORDER_STATE_CANCELED = "canceled",
  BATCH_ORDER_STATE_COMPLETED = "completed",
}

export enum BatchOrderPaymentMethodEnum {
  BATCH_ORDER_WITH_PURCHASE_ORDER = "purchase_order",
  BATCH_ORDER_WITH_BANK_TRANSFER = "bank_transfer",
  BATCH_ORDER_WITH_CARD_PAYMENT = "card_payment",
}

export type BillingAddress = {
  company_name: string;
  identification_number: string;
  address: string;
  postcode: string;
  city: string;
  country: string;
  contact_email: string;
  contact_name: string;
};

export type BatchOrderAction =
  | "confirm_quote"
  | "confirm_purchase_order"
  | "confirm_bank_transfer"
  | "submit_for_signature"
  | "generate_orders"
  | "cancel";

export type BatchOrderAvailableActions = {
  [K in BatchOrderAction]: boolean;
} & {
  next_action: BatchOrderAction | null;
};

export type AbstractBatchOrder = {
  id: string;
  created_on: string;
  updated_on: string;
  state: BatchOrderStatesEnum;
  nb_seats: number;
  total: Nullable<number>;
  total_currency: string;
  payment_method: BatchOrderPaymentMethodEnum;
  available_actions: BatchOrderAvailableActions;
};

export type BatchOrderListItem = AbstractBatchOrder & {
  course_code: Nullable<string>;
  product_title: string;
  company_name: string;
  owner_name: string;
  organization_title: string;
};

export type BatchOrder = AbstractBatchOrder & {
  offering: Offering;
  organization: Nullable<Organization>;
  contract_id: Nullable<string>;
  owner: User;

  identification_number: string;
  vat_registration: Nullable<string>;
  company_name: string;
  address: string;
  postcode: string;
  city: string;
  country: string;

  billing_address: BillingAddress;

  administrative_firstname: string;
  administrative_lastname: string;
  administrative_profession: string;
  administrative_email: string;
  administrative_telephone: string;
  signatory_firstname: string;
  signatory_lastname: string;
  signatory_profession: string;
  signatory_email: string;
  signatory_telephone: string;

  funding_entity: string;
  funding_amount: number;
  orders: OrderListItem[];
};

export type BatchOrderQuery = ResourcesQuery & {};

export const transformBatchOrderToListItem = (
  batchOrder: BatchOrder,
): BatchOrderListItem => {
  return {
    id: batchOrder.id,
    created_on: batchOrder.created_on,
    updated_on: batchOrder.updated_on,
    state: batchOrder.state,
    nb_seats: batchOrder.nb_seats,
    total: batchOrder.total,
    total_currency: batchOrder.total_currency,
    payment_method: batchOrder.payment_method,
    course_code: batchOrder.offering.course.code ?? null,
    product_title: batchOrder.offering.product.title,
    company_name: batchOrder.company_name,
    owner_name: batchOrder.owner.full_name ?? batchOrder.owner.username,
    organization_title: batchOrder.organization?.title ?? "",
    available_actions: batchOrder.available_actions,
  };
};

export const transformBatchOrdersToListItems = (
  batches: BatchOrder[],
): BatchOrderListItem[] => {
  return batches.map(transformBatchOrderToListItem);
};
