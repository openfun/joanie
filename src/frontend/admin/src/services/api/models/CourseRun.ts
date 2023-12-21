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
  uri?: string;
};

export interface DTOCourseRun extends Omit<CourseRun, "course" | "id"> {
  id?: string;
  course_id: string;
}
