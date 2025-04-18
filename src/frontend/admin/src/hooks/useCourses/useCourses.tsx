import { defineMessages, useIntl } from "react-intl";
import { useQuery } from "@tanstack/react-query";
import {
  QueryOptions,
  useResource,
  useResourcesCustom,
  UseResourcesProps,
} from "@/hooks/useResources";
import { ResourcesQuery } from "@/hooks/useResources/types";
import { Course } from "@/services/api/models/Course";
import { CourseRepository } from "@/services/repositories/courses/CoursesRepository";
import { DTOAccesses } from "@/services/api/models/Accesses";
import { SelectOption } from "@/components/presentational/hook-form/RHFSelect";

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

export type CourseResourceQuery = ResourcesQuery & {
  state?: string;
  organization_ids?: string[];
  start?: string;
};

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

export const useCourses = (
  filters?: CourseResourceQuery,
  queryOptions?: QueryOptions<Course>,
) => {
  const custom = useResourcesCustom({ ...props, filters, queryOptions });
  const intl = useIntl();
  const accesses = useAllCourseAccesses();
  return {
    ...custom,
    accesses,
    methods: {
      ...custom.methods,
      addAccessUser: async (courseId: string, user: string, role: string) => {
        const result = await CourseRepository.addUserAccess(
          courseId,
          user,
          role,
        );
        await custom.methods.invalidate();
        return result;
      },
      updateAccessUser: async (
        courseId: string,
        accessId: string,
        payload: DTOAccesses,
      ) => {
        try {
          await CourseRepository.updateUserAccess(courseId, accessId, payload);
          await custom.methods.invalidate();
        } catch (e) {
          custom.methods.setError(
            intl.formatMessage(useCoursesMessages.errorUpdate),
          );
          throw e;
        }
      },
      removeAccessUser: async (courseId: string, accessId: string) => {
        try {
          await CourseRepository.removeUserAccess(courseId, accessId);
          await custom.methods.invalidate();
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
        } catch (_error) {
          custom.methods.setError(
            intl.formatMessage(useCoursesMessages.errorDelete),
          );
        }
      },
    },
  };
};

// eslint-disable-next-line react-hooks/rules-of-hooks
export const useCourse = useResource(props);

export const useAllCourseAccesses = (): SelectOption[] | undefined => {
  const accesses = useQuery({
    queryKey: ["allCourseAccesses"],
    queryFn: async () => {
      return CourseRepository.getAvailableAccesses();
    },
    staleTime: Infinity,
    gcTime: Infinity,
  });

  return accesses?.data ?? undefined;
};
