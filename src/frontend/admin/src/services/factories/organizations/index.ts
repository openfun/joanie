import { faker } from "@faker-js/faker";
import { Organization } from "@/services/api/models/Organization";
import { ThumbnailDetailFactory } from "@/services/factories/images";

const build = (): Organization => {
  return {
    id: faker.string.uuid(),
    title: faker.company.name(),
    code: faker.company.name().substring(0, 3),
    representative: faker.internet.email(),
    signature: ThumbnailDetailFactory(),
    logo: ThumbnailDetailFactory(),
  };
};

export function OrganizationFactory(): Organization;
export function OrganizationFactory(count: number): Organization[];
export function OrganizationFactory(
  count?: number
): Organization | Organization[] {
  if (count) return [...Array(count)].map(build);
  return build();
}
