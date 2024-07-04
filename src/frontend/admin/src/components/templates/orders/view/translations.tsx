import { defineMessages } from "react-intl";
import {
  OrderInvoiceStatusEnum,
  OrderInvoiceTypesEnum,
  OrderStatesEnum,
} from "@/services/api/models/Order";

export const orderViewMessages = defineMessages({
  contract: {
    id: "components.templates.orders.view.contract",
    defaultMessage: "Contract",
    description: "Contract field",
  },
  submittedForSignatureOn: {
    id: "components.templates.orders.view.submittedForSignatureOn",
    defaultMessage: "Submit for signature",
    description: "date of signing on start label input",
  },
  studentSignedOn: {
    id: "components.templates.orders.view.studentSignedOn",
    defaultMessage: "Student signature date",
    description: "Student signature date label field",
  },
  organizationSignedOn: {
    id: "components.templates.orders.view.organizationSignedOn",
    defaultMessage: "Organization signature date",
    description: "Organization signature date label field",
  },
  organization: {
    id: "components.templates.orders.view.organization",
    defaultMessage: "Organization",
    description: "Organization field",
  },
  product: {
    id: "components.templates.orders.view.product",
    defaultMessage: "Product",
    description: "Product field",
  },
  course: {
    id: "components.templates.orders.view.course",
    defaultMessage: "Course",
    description: "Course field",
  },
  owner: {
    id: "components.templates.orders.view.owner",
    defaultMessage: "Owner",
    description: "Owner field",
  },
  enrollment: {
    id: "components.templates.orders.view.enrollment",
    defaultMessage: "Enrollment",
    description: "Enrollment field",
  },
  enrollmentValue: {
    id: "components.templates.orders.view.enrollmentValue",
    defaultMessage:
      "{courseRunTitle} ({courseRunState})\nRegistered on: {registerOn}",
    description: "Enrollment field",
  },
  enrollmentAt: {
    id: "components.templates.orders.view.enrollmentAt",
    defaultMessage: "Registered on",
    description: "Enrollment at text",
  },
  orderGroup: {
    id: "components.templates.orders.view.orderGroup",
    defaultMessage: "Order group",
    description: "Order group field",
  },
  state: {
    id: "components.templates.orders.view.state",
    defaultMessage: "State",
    description: "State field",
  },
  price: {
    id: "components.templates.orders.view.price",
    defaultMessage: "Price",
    description: "Price field",
  },
  total: {
    id: "components.templates.orders.view.total",
    defaultMessage: "Total",
    description: "Total field",
  },
  taxIncluded: {
    id: "components.templates.orders.view.taxIncluded",
    defaultMessage: "tax included",
    description: "Helper text for the price filed",
  },
  hasConsentToTerms: {
    id: "components.templates.orders.view.hasConsentToTerms",
    defaultMessage:
      "The user has accepted the terms and conditions when purchasing",
    description: "Text for the has consent to term label",
  },
  hasNotConsentToTerms: {
    id: "components.templates.orders.view.hasNotConsentToTerms",
    defaultMessage:
      "The user has not accepted the terms and conditions when purchasing",
    description: "Text for the has consent to term label",
  },
  certificate: {
    id: "components.templates.orders.view.certificate",
    defaultMessage: "Certificate",
    description: "Certificate field",
  },
  billingAddress: {
    id: "components.templates.orders.view.billingAddress",
    defaultMessage: "Billing address",
    description: "Billing address field",
  },
  invoiceType: {
    id: "components.templates.orders.view.invoiceType",
    defaultMessage: "Type",
    description: "invoice type field",
  },
  invoiceCreatedOn: {
    id: "components.templates.orders.view.invoiceCreatedOn",
    defaultMessage: "Created on",
    description: "Invoice created on field",
  },
  invoiceUpdatedOn: {
    id: "components.templates.orders.view.invoiceUpdatedOn",
    defaultMessage: "Updated on",
    description: "Invoice updated on field",
  },
  invoiceState: {
    id: "components.templates.orders.view.invoiceState",
    defaultMessage: "State",
    description: "Invoice state field",
  },
  invoiceBalance: {
    id: "components.templates.orders.view.invoiceBalance",
    defaultMessage: "Balance",
    description: "Invoice balance field",
  },
  invoiceRef: {
    id: "components.templates.orders.view.invoiceRef",
    defaultMessage: "Ref:",
    description: "Invoice ref prefix",
  },
  orderDetailsSectionTitle: {
    id: "components.templates.orders.view.orderDetailsSectionTitle",
    defaultMessage: "Order informations",
    description: "Title for the order section",
  },
  contractDetailsSectionTitle: {
    id: "components.templates.orders.view.contractDetailsSectionTitle",
    defaultMessage: "Contract details",
    description: "Title for the contract section",
  },
  certificateDetailsSectionTitle: {
    id: "components.templates.orders.view.certificateDetailsSectionTitle",
    defaultMessage: "Certificate details",
    description: "Title for the certificate section",
  },
  certificateDefinitionTemplate: {
    id: "components.templates.orders.view.certificateDefinitionTemplate",
    defaultMessage: "Certificate template",
    description: "Certificate field",
  },
  certificateDefinitionDate: {
    id: "components.templates.orders.view.certificateDefinitionDate",
    defaultMessage: "Issuance date",
    description: "Issuance date field",
  },
  orderDetailsSectionAlert: {
    id: "components.templates.orders.view.orderDetailsSectionAlert",
    defaultMessage:
      "In this view, you can see the details of an order, such as the user concerned, their status etc.",
    description: "Text for the order details alert",
  },
  invoiceDetailsSectionTitle: {
    id: "components.templates.orders.view.invoiceDetailsSectionTitle",
    defaultMessage: "Invoice details",
    description: "Title for the invoice section",
  },
  invoiceDetailsSectionAlert: {
    id: "components.templates.orders.view.invoiceDetailsSectionAlert",
    defaultMessage:
      "In this section, you have access to the main invoice with its total and balance, as well as sub-invoices (such as credit notes for example)",
    description: "Text for the invoice details alert",
  },
  subInvoiceList: {
    id: "components.templates.orders.view.subInvoiceList",
    defaultMessage: "List of sub-invoices",
    description: "Sub invoice list title",
  },
});

export const invoiceTypesMessages = defineMessages<OrderInvoiceTypesEnum>({
  invoice: {
    id: "components.templates.orders.view.orderTypes.invoice",
    defaultMessage: "Invoice",
    description: "Text for invoice type",
  },
  credit_note: {
    id: "components.templates.orders.view.orderTypes.credit_note",
    defaultMessage: "Credit note",
    description: "Text for credit note type",
  },
});

export const invoiceStatusMessages = defineMessages<OrderInvoiceStatusEnum>({
  unpaid: {
    id: "components.templates.orders.view.orderStatus.unpaid",
    defaultMessage: "Unpaid",
    description: "Text for unpaid status",
  },
  paid: {
    id: "components.templates.orders.view.orderStatus.paid",
    defaultMessage: "Paid",
    description: "Text for paid status",
  },
  refunded: {
    id: "components.templates.orders.view.orderStatus.refunded",
    defaultMessage: "Refunded",
    description: "Text for refunded status",
  },
});

export const orderStatesMessages = defineMessages<OrderStatesEnum>({
  draft: {
    id: "components.templates.orders.view.orderStatesMessages.draft",
    defaultMessage: "Draft",
    description: "Text for draft order state",
  },
  assigned: {
    id: "components.templates.orders.view.orderStatesMessages.assigned",
    defaultMessage: "Assigned",
    description: "Text for assigned order state",
  },
  to_save_payment_method: {
    id: "components.templates.orders.view.orderStatesMessages.to_save_payment_method",
    defaultMessage: "To save payment method",
    description: "Text for to save payment method order state",
  },
  to_sign: {
    id: "components.templates.orders.view.orderStatesMessages.to_sign",
    defaultMessage: "To sign",
    description: "Text for to sign order state",
  },
  signing: {
    id: "components.templates.orders.view.orderStatesMessages.signing",
    defaultMessage: "Signing",
    description: "Text for signing order state",
  },
  pending: {
    id: "components.templates.orders.view.orderStatesMessages.pending",
    defaultMessage: "Pending",
    description: "Text for pending order state",
  },
  canceled: {
    id: "components.templates.orders.view.orderStatesMessages.canceled",
    defaultMessage: "Canceled",
    description: "Text for canceled order state",
  },
  pending_payment: {
    id: "components.templates.orders.view.orderStatesMessages.pending_payment",
    defaultMessage: "Pending payment",
    description: "Text for pending payment order state",
  },
  failed_payment: {
    id: "components.templates.orders.view.orderStatesMessages.failed_payment",
    defaultMessage: "Failed payment",
    description: "Text for failed payment order state",
  },
  no_payment: {
    id: "components.templates.orders.view.orderStatesMessages.no_payment",
    defaultMessage: "No payment",
    description: "Text for no payment order state",
  },
  completed: {
    id: "components.templates.orders.view.orderStatesMessages.completed",
    defaultMessage: "Completed",
    description: "Text for completed order state",
  },
});
