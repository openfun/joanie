import { faker } from "@faker-js/faker";
import { Teacher } from "@/services/api/models/Teacher";

function build(): Teacher {
  return {
    id: faker.string.uuid(),
    first_name: faker.person.firstName(),
    last_name: faker.person.lastName(),
  };
}

export function TeacherFactory(): Teacher;
export function TeacherFactory(count: number): Teacher[];
export function TeacherFactory(count?: number): Teacher | Teacher[] {
  if (count) return [...Array(count)].map(build);
  return build();
}
