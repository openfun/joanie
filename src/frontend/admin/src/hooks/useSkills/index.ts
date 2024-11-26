import {
  ApiResourceInterface,
  ResourcesQuery,
} from "@/hooks/useResources/types";
import {
  useResources,
  UseResourcesProps,
  useResource,
} from "@/hooks/useResources";
import { Skill } from "@/services/api/models/Skill";
import { SkillRepository } from "@/services/repositories/skills/SkillRepository";

export type SkillResourcesQuery = ResourcesQuery;

const props: UseResourcesProps<
  Skill,
  SkillResourcesQuery,
  ApiResourceInterface<Skill, SkillResourcesQuery>
> = {
  queryKey: ["skills"],
  apiInterface: () => ({
    get: async (filters?: ResourcesQuery) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return SkillRepository.get(id, otherFilters);
      }
      return SkillRepository.getAll(filters);
    },
    create: SkillRepository.create,
    update: ({ id, ...payload }) => {
      return SkillRepository.update(id, payload);
    },
  }),
};

// eslint-disable-next-line react-hooks/rules-of-hooks
export const useSkills = useResources(props);
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useSkill = useResource(props);
