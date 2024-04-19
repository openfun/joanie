import { faker } from "@faker-js/faker";
import { CourseRun } from "@/services/api/models/CourseRun";
import {
  CourseFactory,
  CourseStateFactory,
} from "@/services/factories/courses";
import { Course } from "@/services/api/models/Course";

export const buildCourseRun = (course?: Course): CourseRun => {
  return {
    id: faker.string.uuid(),
    title: faker.company.name(),
    course: course ?? CourseFactory(),
    resource_link: faker.internet.url(),
    start: new Date("2023-01-21").toISOString(),
    end: new Date("2024-04-23").toISOString(),
    enrollment_start: new Date("2022-12-01").toISOString(),
    enrollment_end: new Date("2022-12-25").toISOString(),
    languages: ["en-us"],
    is_gradable: faker.datatype.boolean(),
    is_listed: faker.datatype.boolean(),
    state: CourseStateFactory(),
    uri: faker.internet.url(),
  };
};

export function CourseRunFactory(count?: never, course?: Course): CourseRun;
export function CourseRunFactory(count: number, course?: Course): CourseRun[];
export function CourseRunFactory(
  count?: number,
  course?: Course,
): CourseRun | CourseRun[] {
  if (count && count > 0)
    return [...Array(count)].map(() => buildCourseRun(course));
  return buildCourseRun(course);
}
