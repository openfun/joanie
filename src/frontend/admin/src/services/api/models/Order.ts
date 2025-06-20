import { ResourcesQuery } from "@/hooks/useResources";
import { Course } from "@/services/api/models/Course";
import { Organization } from "@/services/api/models/Organization";
import { OfferRule } from "@/services/api/models/OfferRule";
import { User } from "@/services/api/models/User";
import { ProductSimple } from "@/services/api/models/Product";
import { Enrollment } from "@/services/api/models/Enrollment";
import { Nullable } from "@/types/utils";
import { GeneratedCertificate } from "@/services/api/models/GeneratedCertificate";

export type AbstractOrder = {
  id: string;
  created_on: string;
  updated_on: string;
  state: OrderStatesEnum;
  total: number;
  total_currency: string;
};

export type OrderListItem = AbstractOrder & {
  course_code: Nullable<string>;
  enrollment_id: Nullable<string>;
  organization_title: string;
  owner_name: string;
  product_title: string;
};

export enum PaymentStatesEnum {
  PAYMENT_STATE_PENDING = "pending",
  PAYMENT_STATE_PAID = "paid",
  PAYMENT_STATE_REFUSED = "refused",
}

export type OrderPaymentSchedule = {
  id: string;
  amount: number;
  currency: string;
  due_date: string;
  state: PaymentStatesEnum;
};

export type OrderCreditCard = {
  id: string;
  brand: string;
  last_numbers: string;
  expiration_month: number;
  expiration_year: number;
};

export type Order = AbstractOrder & {
  owner: User;
  product: ProductSimple;
  organization?: Organization;
  offer_rule?: OfferRule;
  course: Nullable<Course>;
  enrollment: Nullable<Enrollment>;
  certificate: Nullable<GeneratedCertificate>;
  main_invoice: OrderMainInvoice;
  contract: Nullable<OrderContractDetails>;
  payment_schedule: Nullable<OrderPaymentSchedule[]>;
  credit_card: Nullable<OrderCreditCard>;
  has_waived_withdrawal_right: boolean;
};

export type OrderContractDetails = {
  definition_title: string;
  id: string;
  organization_signed_on: Nullable<string>;
  student_signed_on: Nullable<string>;
  submitted_for_signature_on: Nullable<string>;
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
  ORDER_STATE_ASSIGNED = "assigned", // order has been assigned to an organization
  ORDER_STATE_TO_SAVE_PAYMENT_METHOD = "to_save_payment_method", // order needs a payment method
  ORDER_STATE_TO_SIGN = "to_sign", // order needs a contract signature
  ORDER_STATE_SIGNING = "signing", // order is pending for contract signature validation
  ORDER_STATE_PENDING = "pending", // payment has failed but can be retried
  ORDER_STATE_CANCELED = "canceled", // has been canceled
  ORDER_STATE_PENDING_PAYMENT = "pending_payment", // payment is pending
  ORDER_STATE_TO_OWN = "to_own", // order is paid but is awaiting owner to claim it
  ORDER_STATE_FAILED_PAYMENT = "failed_payment", // last payment has failed
  ORDER_STATE_NO_PAYMENT = "no_payment", // no payment has been made
  ORDER_STATE_COMPLETED = "completed", // is completed
  ORDER_STATE_REFUNDING = "refunding", // is being refunded
  ORDER_STATE_REFUNDED = "refunded", // has been refunded
}

export const transformOrderToOrderListItem = (order: Order): OrderListItem => {
  return {
    id: order.id,
    course_code: order.course?.code ?? null,
    created_on: order.created_on,
    updated_on: order.updated_on,
    enrollment_id: order.enrollment?.id ?? null,
    organization_title: order.organization?.title ?? "",
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
