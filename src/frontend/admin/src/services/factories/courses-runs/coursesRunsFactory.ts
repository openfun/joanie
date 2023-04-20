import { faker } from "@faker-js/faker";
import { CourseRun } from "@/services/api/models/CourseRun";
import {
  createDummyCourse,
  createDummyCourseState,
} from "@/services/factories/courses/courseFactory";

export const createDummyCourseRun = (): CourseRun => {
  return {
    id: faker.datatype.uuid(),
    title: faker.company.name(),
    course: createDummyCourse(),
    resource_link: faker.internet.url(),
    start: new Date("2023-01-21").toISOString(),
    end: new Date("2024-04-23").toISOString(),
    enrollment_start: new Date("2022-12-01").toISOString(),
    enrollment_end: new Date("2022-12-25").toISOString(),
    languages: ["en"],
    is_gradable: faker.datatype.boolean(),
    is_listed: faker.datatype.boolean(),
    state: createDummyCourseState(),
  };
};

export const createDummyCoursesRuns = (number: number = 10): CourseRun[] => {
  return [...Array(number)].map(() => createDummyCourseRun());
};
