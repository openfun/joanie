import moment from "moment";
import { Organization } from "./Organization";
import { CourseProductRelation } from "./Relations";
import { Accesses } from "@/services/api/models/Accesses";
import { CourseRun } from "@/services/api/models/CourseRun";
import { ThumbnailDetailField } from "@/services/api/models/Image";

export type Course = {
  id: string;
  code: string;
  title: string;
  organizations: Organization[];
  is_graded: boolean;
  product_relations?: CourseProductRelation[];
  state?: CourseState;
  courses_runs?: CourseRun[];
  cover?: ThumbnailDetailField;
  accesses?: Accesses<CourseRoles>[];
  effort?: string;
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
  | "cover"
  | "courses_runs"
  | "effort"
  | "is_graded"
  | "product_relations"
> & {
  cover: File[] | undefined;
  effort?: number;
};

export interface DTOCourse {
  id?: string;
  code: string;
  title: string;
  cover?: File;
  organization_ids: string[];
  effort?: string | null;
}

export const transformCourseToDTO = (course: CourseFormValues): DTOCourse => {
  const { cover, effort, ...restCourse } = course;
  const organizationIds = course.organizations.map((item) => {
    return item.id;
  });
  const payload: DTOCourse = {
    ...restCourse,
    organization_ids: organizationIds,
    ...(effort
      ? { effort: moment.duration({ hour: effort }).toISOString() }
      : { effort: null }),
  };

  if (course.cover?.[0] !== undefined) {
    payload.cover = course.cover?.[0];
  }

  return payload;
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
