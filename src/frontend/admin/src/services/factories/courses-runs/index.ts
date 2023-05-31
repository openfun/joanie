import { faker } from "@faker-js/faker";
import { CourseRun } from "@/services/api/models/CourseRun";
import {
  CourseFactory,
  CourseStateFactory,
} from "@/services/factories/courses";

const build = (): CourseRun => {
  return {
    id: faker.datatype.uuid(),
    title: faker.company.name(),
    course: CourseFactory(),
    resource_link: faker.internet.url(),
    start: new Date("2023-01-21").toISOString(),
    end: new Date("2024-04-23").toISOString(),
    enrollment_start: new Date("2022-12-01").toISOString(),
    enrollment_end: new Date("2022-12-25").toISOString(),
    languages: ["en"],
    is_gradable: faker.datatype.boolean(),
    is_listed: faker.datatype.boolean(),
    state: CourseStateFactory(),
  };
};

export function CourseRunFactory(): CourseRun;
export function CourseRunFactory(count: number): CourseRun[];
export function CourseRunFactory(count?: number): CourseRun | CourseRun[] {
  if (count) return [...Array(count)].map(build);
  return build();
}
