import {
  ApiResourceInterface,
  ResourcesQuery,
} from "@/hooks/useResources/types";
import {
  useResources,
  UseResourcesProps,
  useResource,
} from "@/hooks/useResources";
import { OfferingRule } from "@/services/api/models/OfferingRule";
import { OfferingRuleRepository } from "@/services/repositories/offeringRule/OfferingRuleRepository";

export type OfferingRuleQuery = ResourcesQuery & {
  id?: string;
  offeringId?: string;
};

const props: UseResourcesProps<
  OfferingRule,
  OfferingRuleQuery,
  ApiResourceInterface<OfferingRule, OfferingRuleQuery>
> = {
  queryKey: ["offering-rule"],
  apiInterface: () => ({
    get: (filters?: OfferingRuleQuery) => {
      const { id, offeringId, ...otherFilters } = filters ?? {};
      if (id && offeringId) {
        return OfferingRuleRepository.get(id, offeringId, otherFilters);
      }
    },
  }),
};

// eslint-disable-next-line react-hooks/rules-of-hooks
export const useOfferingRules = useResources(props);
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useOfferingRule = useResource(props);
