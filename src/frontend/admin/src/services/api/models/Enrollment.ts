import { CourseRun } from "@/services/api/models/CourseRun";
import { GeneratedCertificate } from "@/services/api/models/GeneratedCertificate";
import { User } from "@/services/api/models/User";

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
  certificate: GeneratedCertificate;
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
