import {
  ApiResourceInterface,
  ResourcesQuery,
} from "@/hooks/useResources/types";
import {
  useResources,
  UseResourcesProps,
  useResource,
} from "@/hooks/useResources";
import { Teacher } from "@/services/api/models/Teacher";
import { TeacherRepository } from "@/services/repositories/teachers/TeacherRepository";

export type TeacherResourcesQuery = ResourcesQuery;

const props: UseResourcesProps<
  Teacher,
  TeacherResourcesQuery,
  ApiResourceInterface<Teacher, TeacherResourcesQuery>
> = {
  queryKey: ["teachers"],
  apiInterface: () => ({
    get: async (filters?: ResourcesQuery) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return TeacherRepository.get(id, otherFilters);
      }
      return TeacherRepository.getAll(filters);
    },
    create: TeacherRepository.create,
    update: async ({ id, ...payload }) => {
      return TeacherRepository.update(id, payload);
    },
  }),
};

// eslint-disable-next-line react-hooks/rules-of-hooks
export const useTeachers = useResources(props);
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useTeacher = useResource(props);
