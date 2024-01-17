import { faker } from "@faker-js/faker";
import {
  Order,
  OrderInvoiceStatusEnum,
  OrderInvoiceTypesEnum,
  OrderListItem,
  OrderStatesEnum,
} from "@/services/api/models/Order";
import { ProductFactoryLight } from "@/services/factories/product";
import { OrganizationFactory } from "@/services/factories/organizations";
import { OrderGroupFactory } from "@/services/factories/order-group";
import { CourseFactory } from "@/services/factories/courses";
import { UsersFactory } from "@/services/factories/users";

const build = (): Order => {
  const totalOrder = faker.number.float({ min: 1, max: 9999 });
  return {
    id: faker.string.uuid(),
    created_on: faker.date.anytime().toString(),
    state: faker.helpers.arrayElement(Object.values(OrderStatesEnum)),
    owner: UsersFactory(),
    product: ProductFactoryLight(),
    organization: OrganizationFactory(),
    order_group: OrderGroupFactory(),
    total: totalOrder,
    total_currency: "EUR",
    course: CourseFactory(),
    certificate: {
      id: faker.string.uuid(),
      definition_title: "Fake definition",
      issued_on: faker.date.anytime().toString(),
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
  };
};

export function OrderFactory(): Order;
export function OrderFactory(count: number): Order[];
export function OrderFactory(count?: number): Order | Order[] {
  if (count) return [...Array(count)].map(build);
  return build();
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
