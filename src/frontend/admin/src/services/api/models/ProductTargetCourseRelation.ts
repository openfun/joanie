import { Course } from "./Course";
import { CourseRun } from "./CourseRun";

export type ProductTargetCourseRelation = {
  course: Course;
  course_runs?: CourseRun[];
  position?: number;
  is_graded: boolean;
};
