import type { Course, CourseState } from "./Course";

export type CourseRun = {
  id: string;
  title: string;
  course: Course;
  resource_link: string;
  start?: string | null;
  end?: string | null;
  enrollment_end?: string | null;
  enrollment_start?: string | null;
  languages: string[];
  is_gradable: boolean;
  is_listed: boolean;
  state?: CourseState;
};

export interface DTOCourseRun extends Omit<CourseRun, "course"> {
  course: string;
}
