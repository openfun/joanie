import { ResourcesQuery } from "@/hooks/useResources";
import { Course } from "@/services/api/models/Course";
import { Organization } from "@/services/api/models/Organization";
import { OrderGroup } from "@/services/api/models/OrderGroup";
import { User } from "@/services/api/models/User";
import { Product } from "@/services/api/models/Product";
import { Enrollment } from "@/services/api/models/Enrollment";

export type AbstractOrder = {
  id: string;
  created_on: string;
  state: OrderStatesEnum;
  total: number;
  total_currency: string;
};

export type OrderListItem = AbstractOrder & {
  course_code?: string;
  enrollment_id?: string;
  organization_title: string;
  owner_name: string;
  product_title: string;
};

export type Order = AbstractOrder & {
  owner: User;
  product: Product;
  organization: Organization;
  order_group?: OrderGroup;
  course?: Course;
  enrollment?: Enrollment;
  certificate: {
    id: string;
    definition_title: string;
    issued_on: string;
  };
  main_invoice: OrderMainInvoice;
};

export type OrderMainInvoice = {
  balance: string;
  created_on: string;
  updated_on: string;
  state: OrderInvoiceStatusEnum;
  recipient_address: string;
  invoiced_balance: string;
  transactions_balance: string;
  total: number;
  total_currency: string;
  reference: string;
  type: OrderInvoiceTypesEnum;
  children: OrderMainInvoiceChildren[];
};

export type OrderMainInvoiceChildren = {
  balance: number;
  created_on: string;
  invoiced_balance: number;
  recipient_address: string;
  reference: string;
  state: OrderInvoiceStatusEnum;
  transactions_balance: number;
  total: number;
  total_currency: string;
  type: OrderInvoiceTypesEnum;
  updated_on: string;
};

export type OrderListQuery = ResourcesQuery & {};

export type OrderQuery = ResourcesQuery & {};

export enum OrderInvoiceTypesEnum {
  INVOICE = "invoice",
  CREDIT_NOTE = "credit_note",
}

export enum OrderInvoiceStatusEnum {
  INVOICE_STATE_UNPAID = "unpaid",
  INVOICE_STATE_PAID = "paid",
  INVOICE_STATE_REFUNDED = "refunded",
}

export enum OrderStatesEnum {
  ORDER_STATE_DRAFT = "draft", // order has been created
  ORDER_STATE_SUBMITTED = "submitted", // order information have been validated
  ORDER_STATE_PENDING = "pending", // payment has failed but can be retried
  ORDER_STATE_CANCELED = "canceled", // has been canceled
  ORDER_STATE_VALIDATED = "validated", // is free or has an invoice linked
}

export const transformOrderToOrderListItem = (order: Order): OrderListItem => {
  return {
    id: order.id,
    course_code: order.course?.code,
    created_on: order.created_on,
    enrollment_id: order.enrollment?.id,
    organization_title: order.organization.title,
    owner_name: order.owner.full_name ?? order.owner.username,
    product_title: order.product.title,
    state: order.state,
    total: order.total,
    total_currency: order.total_currency,
  };
};

export const transformOrdersToOrderListItems = (
  orders: Order[],
): OrderListItem[] => {
  const result: OrderListItem[] = [];
  orders.forEach((order) => result.push(transformOrderToOrderListItem(order)));
  return result;
};
