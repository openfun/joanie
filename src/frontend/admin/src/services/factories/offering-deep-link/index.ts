import { faker } from "@faker-js/faker";
import { OfferingDeepLink } from "@/services/api/models/OfferingDeepLink";

const build = (): OfferingDeepLink => ({
  id: faker.string.uuid(),
  deep_link: faker.internet.url(),
  is_active: faker.datatype.boolean(),
  offering: faker.string.uuid(),
  organization: faker.string.uuid(),
});

export function OfferingDeepLinkFactory(): OfferingDeepLink;
export function OfferingDeepLinkFactory(count: number): OfferingDeepLink[];
export function OfferingDeepLinkFactory(
  count?: number,
): OfferingDeepLink | OfferingDeepLink[] {
  if (count) return [...Array(count)].map(() => build());
  return build();
}
