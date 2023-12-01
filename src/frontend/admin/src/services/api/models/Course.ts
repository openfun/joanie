import { Organization } from "./Organization";
import { CourseRelationToProduct } from "./Relations";
import { Accesses } from "@/services/api/models/Accesses";
import { CourseRun } from "@/services/api/models/CourseRun";

export type Course = {
  id: string;
  code: string;
  title: string;
  organizations: Organization[];
  is_graded: boolean;
  product_relations?: CourseRelationToProduct[];
  state?: CourseState;
  courses_runs?: CourseRun[];
  accesses?: Accesses<CourseRoles>[];
};

export enum CourseRoles {
  OWNER = "owner",
  ADMIN = "administrator",
  INSTRUCTOR = "instructor",
  MANAGER = "manager",
}

export type CourseFormValues = Omit<
  Course,
  | "accesses"
  | "id"
  | "state"
  | "courses_runs"
  | "is_graded"
  | "product_relations"
>;

export interface DTOCourse {
  id?: string;
  code: string;
  title: string;
  organization_ids: string[];
  // product_relations?: DTOCourseRelationToProduct[];
}

export const transformCourseToDTO = (course: CourseFormValues): DTOCourse => {
  const organizationIds = course.organizations.map((item) => {
    return item.id;
  });

  return {
    ...course,
    organization_ids: organizationIds,
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
