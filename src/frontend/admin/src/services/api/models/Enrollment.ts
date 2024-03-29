import { CourseRun } from "@/services/api/models/CourseRun";
import { GeneratedCertificate } from "@/services/api/models/GeneratedCertificate";
import { User } from "@/services/api/models/User";
import { Nullable } from "@/types/utils";

export type BaseEnrollment = {
  id: string;
  course_run: CourseRun;
  state: EnrollmentState;
  is_active: boolean;
};

export type EnrollmentListItem = BaseEnrollment & {
  user_name: string;
};

export type Enrollment = BaseEnrollment & {
  created_on: string;
  updated_on: string;
  certificate: Nullable<GeneratedCertificate>;
  user: User;
  was_created_by_order: boolean;
};

export type DTOEnrollment = {
  is_active: boolean;
};

export enum EnrollmentState {
  SET = "set",
  FAILED = "failed",
}

export const transformEnrollmentToEnrollmentListItem = (
  enrollment: Enrollment,
): EnrollmentListItem => {
  return {
    id: enrollment.id,
    course_run: enrollment.course_run,
    state: enrollment.state,
    is_active: enrollment.is_active,
    user_name: enrollment.user.full_name ?? enrollment.user.username,
  };
};

export const transformEnrollmentsToEnrollmentListItems = (
  enrollments: Enrollment[],
): EnrollmentListItem[] => {
  const result: EnrollmentListItem[] = [];
  enrollments.forEach((enrollment) =>
    result.push(transformEnrollmentToEnrollmentListItem(enrollment)),
  );
  return result;
};
