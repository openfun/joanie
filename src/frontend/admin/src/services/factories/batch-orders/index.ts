import { faker } from "@faker-js/faker";
import {
  BatchOrder,
  BatchOrderListItem,
  BatchOrderStatesEnum,
} from "@/services/api/models/BatchOrder";
import { OfferingFactory } from "@/services/api/models/Offerings";
import { OrganizationFactory } from "@/services/factories/organizations";
import { UsersFactory } from "@/services/factories/users";

const build = (state?: BatchOrderStatesEnum): BatchOrder => {
  const totalOrder = faker.number.float({ min: 1, max: 9999 });
  state =
    state || faker.helpers.arrayElement(Object.values(BatchOrderStatesEnum));

  const offering = OfferingFactory();
  const organization = OrganizationFactory();
  const owner = UsersFactory();

  const batchOrder: BatchOrder = {
    id: faker.string.uuid(),
    created_on: faker.date.anytime().toString(),
    updated_on: faker.date.anytime().toString(),
    state,
    nb_seats: faker.number.int({ min: 1, max: 100 }),
    total: totalOrder,
    total_currency: "EUR",
    offering,
    organization,
    contract_id: faker.string.uuid(),
    owner,
    identification_number: faker.string.alphanumeric({ length: 14 }),
    vat_registration: faker.string.alphanumeric({ length: 13 }),
    company_name: faker.company.name(),
    address: faker.location.streetAddress(),
    postcode: faker.location.zipCode(),
    city: faker.location.city(),
    country: faker.location.country(),
    administrative_firstname: faker.person.firstName(),
    administrative_lastname: faker.person.lastName(),
    administrative_profession: faker.person.jobTitle(),
    administrative_email: faker.internet.email(),
    administrative_telephone: faker.phone.number(),
    signatory_firstname: faker.person.firstName(),
    signatory_lastname: faker.person.lastName(),
    signatory_profession: faker.person.jobTitle(),
    signatory_email: faker.internet.email(),
    signatory_telephone: faker.phone.number(),
    funding_entity: faker.company.name(),
    funding_amount: faker.number.float({ min: 0, max: totalOrder }),
  };

  return batchOrder;
};

export function BatchOrderFactory(): BatchOrder;
export function BatchOrderFactory(
  count: number,
  state?: BatchOrderStatesEnum,
): BatchOrder[];
export function BatchOrderFactory(
  count?: number,
  state?: BatchOrderStatesEnum,
): BatchOrder | BatchOrder[] {
  if (count) return [...Array(count)].map(() => build(state));
  return build(state);
}

const buildBatchOrderListItem = (): BatchOrderListItem => {
  const offering = OfferingFactory();
  const organization = OrganizationFactory();
  const owner = UsersFactory();

  return {
    id: faker.string.uuid(),
    created_on: faker.date.anytime().toString(),
    updated_on: faker.date.anytime().toString(),
    state: faker.helpers.arrayElement(Object.values(BatchOrderStatesEnum)),
    nb_seats: faker.number.int({ min: 1, max: 100 }),
    total: faker.number.float({ min: 1, max: 9999 }),
    total_currency: "EUR",
    course_code: offering.course.code ?? null,
    product_title: offering.product.title,
    company_name: faker.company.name(),
    owner_name: owner.full_name ?? owner.username,
    organization_title: organization.title,
  };
};

export function BatchOrderListItemFactory(): BatchOrderListItem;
export function BatchOrderListItemFactory(count: number): BatchOrderListItem[];
export function BatchOrderListItemFactory(
  count?: number,
): BatchOrderListItem | BatchOrderListItem[] {
  if (count) return [...Array(count)].map(buildBatchOrderListItem);
  return buildBatchOrderListItem();
}
