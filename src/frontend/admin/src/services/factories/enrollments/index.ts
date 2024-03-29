import { faker } from "@faker-js/faker";
import { UsersFactory } from "@/services/factories/users";
import {
  BaseEnrollment,
  Enrollment,
  EnrollmentListItem,
  EnrollmentState,
} from "@/services/api/models/Enrollment";
import { CourseRunFactory } from "@/services/factories/courses-runs";

const buildBaseEnrollment = (): BaseEnrollment => {
  return {
    id: faker.string.uuid(),
    is_active: faker.datatype.boolean(),
    course_run: CourseRunFactory(),
    state: faker.helpers.arrayElement(Object.values(EnrollmentState)),
  };
};

const build = (): Enrollment => {
  return {
    ...buildBaseEnrollment(),
    created_on: faker.date.anytime().toString(),
    updated_on: faker.date.anytime().toString(),
    certificate: null,
    user: UsersFactory(),
    was_created_by_order: faker.datatype.boolean(),
  };
};

export function EnrollmentFactory(): Enrollment;
export function EnrollmentFactory(count: number): Enrollment[];
export function EnrollmentFactory(count?: number): Enrollment | Enrollment[] {
  if (count) return [...Array(count)].map(build);
  return build();
}

const buildEnrollmentListItem = (): EnrollmentListItem => {
  return {
    ...buildBaseEnrollment(),
    user_name: faker.person.fullName(),
  };
};

export function EnrollmentListItemFactory(): EnrollmentListItem;
export function EnrollmentListItemFactory(count: number): EnrollmentListItem[];
export function EnrollmentListItemFactory(
  count?: number,
): EnrollmentListItem | EnrollmentListItem[] {
  if (count) return [...Array(count)].map(buildEnrollmentListItem);
  return buildEnrollmentListItem();
}
