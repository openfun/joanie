import { ResourcesQuery } from "@/hooks/useResources";
import { Organization } from "@/services/api/models/Organization";
import { Nullable } from "@/types/utils";
import { User } from "@/services/api/models/User";
import { Offering } from "@/services/api/models/Offerings";

export enum BatchOrderStatesEnum {
  BATCH_ORDER_STATE_DRAFT = "draft",
  BATCH_ORDER_STATE_ASSIGNED = "assigned",
  BATCH_ORDER_STATE_QUOTED = "quoted",
  BATCH_ORDER_STATE_TO_SIGN = "to_sign",
  BATCH_ORDER_STATE_SIGNING = "signing",
  BATCH_ORDER_STATE_PENDING = "pending",
  BATCH_ORDER_STATE_FAILED_PAYMENT = "failed_payment",
  BATCH_ORDER_STATE_CANCELED = "canceled",
  BATCH_ORDER_STATE_COMPLETED = "completed",
}

export type AbstractBatchOrder = {
  id: string;
  created_on: string;
  updated_on: string;
  state: BatchOrderStatesEnum;
  nb_seats: number;
  total: number;
  total_currency: string;
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
};

export type BatchOrderQuery = ResourcesQuery & {};

export const transformBatchOrderToListItem = (
  batchOrder: BatchOrder,
): BatchOrderListItem => {
  return {
    id: batchOrder.id,
    created_on: batchOrder.created_on ?? "",
    updated_on: batchOrder.updated_on ?? "",
    state: batchOrder.state ?? "",
    nb_seats: batchOrder.nb_seats,
    total: batchOrder.total,
    total_currency: batchOrder.total_currency,
    course_code: batchOrder.offering.course.code ?? null,
    product_title: batchOrder.offering.product.title,
    company_name: batchOrder.company_name,
    owner_name: batchOrder.owner.full_name ?? batchOrder.owner.username,
    organization_title: batchOrder.organization?.title ?? "",
  };
};

export const transformBatchOrdersToListItems = (
  batches: BatchOrder[],
): BatchOrderListItem[] => {
  return batches.map(transformBatchOrderToListItem);
};
