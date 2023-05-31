import { Organization } from "./Organization";
import {
  CourseRelationToProduct,
  DTOCourseRelationToProduct,
} from "./Relations";
import { CourseRun } from "./CourseRun";

export type Course = {
  id: string;
  code: string;
  title: string;
  organizations: Organization[];
  product_relations?: CourseRelationToProduct[];
  state?: CourseState;
  courses_runs?: CourseRun[];
};

export type CourseFormValue = Omit<Course, "id">;

export interface DTOCourse {
  id?: string;
  code: string;
  title: string;
  organizations: string[];
  product_relations?: DTOCourseRelationToProduct[];
  courses_runs?: string[];
}

export const transformCourseToDTO = (
  course: Course | CourseFormValue
): DTOCourse => {
  const coursesRunsIds = course.courses_runs?.map((item) => {
    return item.id;
  });

  const organizationIds = course.organizations.map((item) => {
    return item.id;
  });

  const productRelations = course.product_relations?.map((item) => {
    const orgsIds = item.organizations.map((org) => {
      return org.id;
    });
    const result: DTOCourseRelationToProduct = {
      product: item.product.id,
      organizations: orgsIds,
    };
    return result;
  });

  return {
    ...course,
    organizations: organizationIds,
    courses_runs: coursesRunsIds,
    product_relations: productRelations ?? [],
  };
};

export interface CourseState {
  priority: Priority;
  datetime: string;
  call_to_action: StateCTA;
  text: StateText;
}

export enum Priority {
  ONGOING_OPEN,
  FUTURE_OPEN,
  ARCHIVED_OPEN,
  FUTURE_NOT_YET_OPEN,
  FUTURE_CLOSED,
  ONGOING_CLOSED,
  ARCHIVED_CLOSED,
  TO_BE_SCHEDULED,
}

export type StateText =
  | "closing on"
  | "starting on"
  | "enrollment closed"
  | "on-going"
  | "archived"
  | "to be scheduled";

export type StateCTA = "enroll now" | "study now" | undefined;
