import { faker } from "@faker-js/faker";
import {
  Order,
  OrderInvoiceStatusEnum,
  OrderInvoiceTypesEnum,
  OrderListItem,
  OrderPaymentSchedule,
  OrderStatesEnum,
  PaymentStatesEnum,
} from "@/services/api/models/Order";
import {
  ProductFactoryLight,
  ProductSimpleFactory,
} from "@/services/factories/product";
import { OrganizationFactory } from "@/services/factories/organizations";
import { OrderGroupFactory } from "@/services/factories/order-group";
import { CourseFactory } from "@/services/factories/courses";
import { UsersFactory } from "@/services/factories/users";
import { CreditCardFactory } from "@/services/factories/credit-cards";

const orderPayment = (
  due_date: string,
  amount: number,
): OrderPaymentSchedule => {
  return {
    id: faker.string.uuid(),
    amount,
    currency: "EUR",
    due_date,
    state: PaymentStatesEnum.PAYMENT_STATE_PENDING,
  };
};

const build = (state?: OrderStatesEnum): Order => {
  const totalOrder = faker.number.float({ min: 1, max: 9999 });
  state = state || faker.helpers.arrayElement(Object.values(OrderStatesEnum));
  const order: Order = {
    id: faker.string.uuid(),
    created_on: faker.date.anytime().toString(),
    state,
    owner: UsersFactory(),
    product: ProductSimpleFactory(),
    organization: OrganizationFactory(),
    order_group: OrderGroupFactory(),
    enrollment: null,
    total: totalOrder,
    total_currency: "EUR",
    course: CourseFactory(),
    certificate: {
      id: faker.string.uuid(),
      definition_title: "Fake definition",
      issued_on: faker.date.anytime().toString(),
    },
    contract: {
      definition_title: "Fake contract definition",
      id: faker.string.uuid(),
      organization_signed_on: faker.date.anytime().toString(),
      student_signed_on: faker.date.anytime().toString(),
      submitted_for_signature_on: faker.date.anytime().toString(),
    },
    main_invoice: {
      balance: "0",
      created_on: faker.date.anytime().toString(),
      updated_on: faker.date.anytime().toString(),
      state: faker.helpers.arrayElement(Object.values(OrderInvoiceStatusEnum)),
      recipient_address: faker.location.streetAddress(),
      invoiced_balance: totalOrder + "",
      transactions_balance: "0",
      total: totalOrder,
      total_currency: "EUR",
      reference: faker.string.alphanumeric({ length: { min: 5, max: 30 } }),
      type: faker.helpers.arrayElement(Object.values(OrderInvoiceTypesEnum)),
      children: [],
    },
    payment_schedule: [
      orderPayment("6/27/2024", totalOrder / 3),
      orderPayment("7/27/2024", totalOrder / 3),
      orderPayment("8/27/2024", totalOrder / 3),
    ],
    credit_card: CreditCardFactory(),
    has_waived_withdrawal_right: faker.datatype.boolean(),
  };
  if (
    ![
      OrderStatesEnum.ORDER_STATE_PENDING,
      OrderStatesEnum.ORDER_STATE_NO_PAYMENT,
      OrderStatesEnum.ORDER_STATE_PENDING_PAYMENT,
      OrderStatesEnum.ORDER_STATE_FAILED_PAYMENT,
      OrderStatesEnum.ORDER_STATE_COMPLETED,
      OrderStatesEnum.ORDER_STATE_CANCELED,
    ].includes(state)
  ) {
    order.credit_card = null;
  }
  if (state === OrderStatesEnum.ORDER_STATE_COMPLETED)
    order.payment_schedule!.forEach((installment) => {
      installment.state = PaymentStatesEnum.PAYMENT_STATE_PAID;
    });
  if (state === OrderStatesEnum.ORDER_STATE_PENDING_PAYMENT)
    order.payment_schedule![0].state = PaymentStatesEnum.PAYMENT_STATE_PAID;
  if (state === OrderStatesEnum.ORDER_STATE_NO_PAYMENT)
    order.payment_schedule![0].state = PaymentStatesEnum.PAYMENT_STATE_REFUSED;
  if (state === OrderStatesEnum.ORDER_STATE_FAILED_PAYMENT) {
    order.payment_schedule![0].state = PaymentStatesEnum.PAYMENT_STATE_PAID;
    order.payment_schedule![1].state = PaymentStatesEnum.PAYMENT_STATE_REFUSED;
  }
  return order;
};

export function OrderFactory(): Order;
export function OrderFactory(count: number, state?: OrderStatesEnum): Order[];
export function OrderFactory(
  count?: number,
  state?: OrderStatesEnum,
): Order | Order[] {
  if (count) return [...Array(count)].map(build);
  return build(state);
}

const buildOrderListItem = (): OrderListItem => {
  return {
    id: faker.string.uuid(),
    course_code: CourseFactory().code,
    created_on: faker.date.anytime().toString(),
    enrollment_id: faker.string.uuid(),
    organization_title: OrganizationFactory().title,
    owner_name: UsersFactory().full_name,
    product_title: ProductFactoryLight().title,
    state: faker.helpers.arrayElement(Object.values(OrderStatesEnum)),
    total: faker.number.float({ min: 1, max: 9999 }),
    total_currency: "EUR",
  };
};

export function OrderListItemFactory(): OrderListItem;
export function OrderListItemFactory(count: number): OrderListItem[];
export function OrderListItemFactory(
  count?: number,
): OrderListItem | OrderListItem[] {
  if (count) return [...Array(count)].map(buildOrderListItem);
  return buildOrderListItem();
}
