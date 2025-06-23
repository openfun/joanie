import { faker } from "@faker-js/faker";
import {
  Course,
  CourseRoles,
  CourseState,
  Priority,
} from "@/services/api/models/Course";
import { OrganizationFactory } from "@/services/factories/organizations";
import { OfferingFactory } from "@/services/api/models/Offerings";
import { AccessesFactory } from "@/services/factories/accesses";
import { CourseRunFactory } from "@/services/factories/courses-runs";

const build = (): Course => {
  const result: Course = {
    id: faker.string.uuid(),
    title: faker.company.name(),
    code: faker.color.rgb(),
    is_graded: true,
    organizations: OrganizationFactory(2),
    offerings: OfferingFactory(1),
    state: CourseStateFactory(),
    accesses: AccessesFactory(Object.values(CourseRoles), 3),
  };

  return {
    ...result,
    courses_runs: CourseRunFactory(2, result),
  };
};

export function CourseFactory(): Course;
export function CourseFactory(count: number): Course[];
export function CourseFactory(count?: number): Course | Course[] {
  if (count) return [...Array(count)].map(build);
  return build();
}

const buildCourseLight = (): Course => {
  const result: Course = {
    id: faker.string.uuid(),
    title: faker.company.name(),
    code: faker.color.rgb(),
    is_graded: true,
    organizations: OrganizationFactory(2),
    state: CourseStateFactory(),
    accesses: [],
  };

  return {
    ...result,
    courses_runs: CourseRunFactory(2, result),
  };
};

export function CourseFactoryLight(): Course;
export function CourseFactoryLight(count: number): Course[];
export function CourseFactoryLight(count?: number): Course | Course[] {
  if (count) return [...Array(count)].map(build);
  return buildCourseLight();
}

export const CourseStateFactory = (): CourseState => {
  return {
    priority: Priority.ONGOING_CLOSED,
    datetime: new Date().toISOString(),
    call_to_action: "enroll now",
    text: "closing on",
  };
};
