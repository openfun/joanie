import { defineMessages } from "react-intl";
import {
  useResource,
  useResources,
  UseResourcesProps,
} from "@/hooks/useResources";
import { Course } from "@/services/api/models/Course";
import { CourseRepository } from "@/services/repositories/courses/CoursesRepository";

export const useCoursesMessages = defineMessages({
  errorUpdate: {
    id: "hooks.useCourse.errorUpdate",
    description:
      "Error message shown to the user when course update request fails.",
    defaultMessage:
      "An error occurred while updating the course. Please retry later.",
  },
  errorGet: {
    id: "hooks.useCourse.errorSelect",
    description:
      "Error message shown to the user when courses fetch request fails.",
    defaultMessage:
      "An error occurred while fetching courses. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useCourse.errorDelete",
    description:
      "Error message shown to the user when course deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the course. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useCourse.errorCreate",
    description:
      "Error message shown to the user when course creation request fails.",
    defaultMessage:
      "An error occurred while creating the course. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useCourse.errorNotFound",
    description: "Error message shown to the user when no courses matches.",
    defaultMessage: "Cannot find the course",
  },
});

/** const course = useCourse();
 * Joanie Api hook to retrieve/create/update/delete courses
 * owned by the authenticated user.
 */
const props: UseResourcesProps<Course> = {
  queryKey: ["courses"],
  apiInterface: () => ({
    get: async (filters) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return CourseRepository.get(id, otherFilters);
      } else {
        return CourseRepository.getAll(filters);
      }
    },
    create: CourseRepository.create,
    update: async ({ id, ...payload }) => {
      return CourseRepository.update(id, payload);
    },
    delete: async (id: string) => {
      return CourseRepository.delete(id);
    },
  }),
  omniscient: false,
  session: true,
  messages: useCoursesMessages,
};
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useCourses = useResources(props);
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useCourse = useResource(props);
