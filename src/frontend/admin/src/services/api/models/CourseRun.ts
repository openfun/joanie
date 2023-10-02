import type { Course, CourseState } from "./Course";
import { courseRunStateTranslations } from "@/translations/course-run/course-run-priority-tranlsations";

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

export enum CourseRunPriority {
  ONGOING_OPEN,
  FUTURE_OPEN,
  ARCHIVED_OPEN,
  FUTURE_NOT_YET_OPEN,
  FUTURE_CLOSED,
  ONGOING_CLOSED,
  ARCHIVED_CLOSED,
  TO_BE_SCHEDULED,
}

export const courseRunStates = [
  {
    label: courseRunStateTranslations.openForEnrollment,
    states: [
      CourseRunPriority.ONGOING_OPEN,
      CourseRunPriority.FUTURE_OPEN,
      CourseRunPriority.ARCHIVED_OPEN,
    ],
  },
  {
    label: courseRunStateTranslations.comingSoon,
    states: [
      CourseRunPriority.FUTURE_NOT_YET_OPEN,
      CourseRunPriority.FUTURE_CLOSED,
      CourseRunPriority.ONGOING_CLOSED,
    ],
  },
  {
    label: courseRunStateTranslations.onGoing,
    states: [CourseRunPriority.ONGOING_OPEN, CourseRunPriority.ONGOING_CLOSED],
  },
  {
    label: courseRunStateTranslations.archived,
    states: [
      CourseRunPriority.ARCHIVED_OPEN,
      CourseRunPriority.ARCHIVED_CLOSED,
    ],
  },
  {
    label: courseRunStateTranslations.toBeScheduled,
    states: [CourseRunPriority.TO_BE_SCHEDULED],
  },
];

export interface DTOCourseRun extends Omit<CourseRun, "course" | "id"> {
  id?: string;
  course: string;
}
