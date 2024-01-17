import { CourseRun } from "@/services/api/models/CourseRun";

export type Enrollment = {
  id: string;
  course_run: CourseRun;
  created_on: string;
  is_active: boolean;
  state: string;
  updated_on: string;
  was_created_by_order: boolean;
};
