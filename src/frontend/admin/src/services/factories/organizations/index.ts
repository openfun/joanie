import { faker } from "@faker-js/faker";
import {
  Organization,
  OrganizationRoles,
} from "@/services/api/models/Organization";
import { ThumbnailDetailFactory } from "@/services/factories/images";
import { AccessesFactory } from "@/services/factories/accesses";

const build = (): Organization => {
  return {
    id: faker.string.uuid(),
    title: faker.company.name(),
    code: faker.number.hex({ min: 0, max: 65535 }),
    representative: faker.internet.email(),
    signature: ThumbnailDetailFactory(),
    logo: ThumbnailDetailFactory(),
    accesses: AccessesFactory(Object.values(OrganizationRoles), 4),
    country: "FR",
  };
};

export function OrganizationFactory(): Organization;
export function OrganizationFactory(count: number): Organization[];
export function OrganizationFactory(
  count?: number,
): Organization | Organization[] {
  if (count) return [...Array(count)].map(build);
  return build();
}
