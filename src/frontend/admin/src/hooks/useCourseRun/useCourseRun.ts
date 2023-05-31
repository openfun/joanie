import { defineMessages } from "react-intl";
import {
  useResource,
  useResources,
  UseResourcesProps,
} from "@/hooks/useResources";
import { CourseRun } from "@/services/api/models/CourseRun";
import { CoursesRunsRepository } from "@/services/repositories/courses-runs/CoursesRunsRepository";

export const useCourseRunMessages = defineMessages({
  errorUpdate: {
    id: "hooks.useCourseRun.errorUpdate",
    description:
      "Error message shown to the user when course run update request fails.",
    defaultMessage:
      "An error occurred while updating the course run. Please retry later.",
  },
  errorGet: {
    id: "hooks.useCourseRun.errorSelect",
    description:
      "Error message shown to the user when course-runs fetch request fails.",
    defaultMessage:
      "An error occurred while fetching course-runs. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useCourseRun.errorDelete",
    description:
      "Error message shown to the user when course-run deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the course-run. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useCourseRun.errorCreate",
    description:
      "Error message shown to the user when course-run creation request fails.",
    defaultMessage:
      "An error occurred while creating the course-run. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useCourseRun.errorNotFound",
    description: "Error message shown to the user when no course-runs matches.",
    defaultMessage: "Cannot find the course-run",
  },
});

/** const certifs = useCourseRun();
 * Joanie Api hook to retrieve/create/update/delete course-runs
 * owned by the authenticated user.
 */
const props: UseResourcesProps<CourseRun> = {
  queryKey: ["coursesRuns"],
  apiInterface: () => ({
    get: async (filters) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return CoursesRunsRepository.get(id, otherFilters);
      } else {
        return CoursesRunsRepository.getAll(filters);
      }
    },
    create: CoursesRunsRepository.create,
    update: async ({ id, ...payload }) => {
      return CoursesRunsRepository.update(id, payload);
    },
    delete: async (id: string) => {
      return CoursesRunsRepository.delete(id);
    },
  }),
  omniscient: false,
  session: true,
  messages: useCourseRunMessages,
};
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useCoursesRuns = useResources(props);
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useCourseRun = useResource(props);
