import { faker } from "@faker-js/faker";
import { Accesses } from "@/services/api/models/Accesses";
import { UsersFactory } from "@/services/factories/users";

const build = <T extends string>(roles: T[]): Accesses<T> => {
  return {
    id: faker.string.uuid(),
    role: faker.helpers.arrayElement(roles),
    user: UsersFactory(),
  };
};

export function AccessesFactory<T extends string>(roles: T[]): Accesses<T>;
export function AccessesFactory<T extends string>(
  roles: T[],
  count: number,
): Accesses<T>[];
export function AccessesFactory<T extends string>(
  roles: T[],
  count: number = 1,
): Accesses<T> | Accesses<T>[] {
  if (count > 1) return [...Array(count)].map(() => build(roles));
  return build(roles);
}
