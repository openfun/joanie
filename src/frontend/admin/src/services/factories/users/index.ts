import { faker } from "@faker-js/faker";
import { User } from "@/services/api/models/User";

const build = (): User => {
  return {
    id: faker.string.uuid(),
    username: faker.internet.userName(),
    fullname: faker.person.fullName(),
  };
};

export function UsersFactory(): User;
export function UsersFactory(count: number): User[];
export function UsersFactory(count?: number): User | User[] {
  if (count) return [...Array(count)].map(build);
  return build();
}
