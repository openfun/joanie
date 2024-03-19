import type { QueryKey, UseQueryOptions } from "@tanstack/react-query";
import { QueryClient } from "@tanstack/react-query";
import { MessageDescriptor } from "react-intl";
import { useResourcesOmniscient } from "./useResourcesOmniscient";
import { useResourcesRoot } from "./useResourcesRoot";
import { ApiResourceInterface } from "@/hooks/useResources/types";
import { HttpError } from "@/services/http/HttpError";

export interface ResourcesQuery {
  ids?: string[];
  id?: string;
  query?: string;
  page?: number;
}

export interface Resource {
  id?: string;
}

export type QueryOptions<TData extends Resource> = Omit<
  UseQueryOptions<unknown, HttpError, TData[]>,
  "queryKey" | "queryFn"
>;

export interface UseResourcesProps<
  TData extends Resource,
  TResourceQuery extends ResourcesQuery = ResourcesQuery,
  TApiResource extends
    ApiResourceInterface<TData> = ApiResourceInterface<TData>,
> {
  queryKey: QueryKey;
  filters?: TResourceQuery;
  apiInterface: () => TApiResource;
  omniscient?: boolean;
  omniscientFiltering?: (data: TData[], filters: TResourceQuery) => TData[];
  session?: boolean;
  localized?: boolean;
  messages?: Record<string, MessageDescriptor>;
  queryOptions?: QueryOptions<TData>;
  frozenQueryKey?: boolean;
  onMutationSuccess?: (queryClient: QueryClient) => void;
}

export const useResourcesCustom = <
  TData extends Resource,
  TResourceQuery extends ResourcesQuery = ResourcesQuery,
  TApiResource extends
    ApiResourceInterface<TData> = ApiResourceInterface<TData>,
>(
  props: UseResourcesProps<TData, TResourceQuery, TApiResource>,
) => {
  if (props.omniscient) {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    return useResourcesOmniscient(props);
  }
  // eslint-disable-next-line react-hooks/rules-of-hooks
  return useResourcesRoot(props);
};

export const useResources =
  <
    TData extends Resource,
    TResourceQuery extends ResourcesQuery = ResourcesQuery,
    TApiResource extends
      ApiResourceInterface<TData> = ApiResourceInterface<TData>,
  >(
    props: UseResourcesProps<TData, TResourceQuery, TApiResource>,
  ) =>
  (filters?: TResourceQuery, queryOptions?: QueryOptions<TData>) => {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    return useResourcesCustom({ ...props, filters, queryOptions });
  };

export const useResource =
  <
    TData extends Resource,
    TResourceQuery extends ResourcesQuery = ResourcesQuery,
  >(
    props: UseResourcesProps<TData>,
  ) =>
  (
    id?: string,
    filters?: Omit<TResourceQuery, "id">,
    queryOptions?: QueryOptions<TData>,
  ) => {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const resources = useResources<TData>(props);
    const res = resources(
      { id, ...filters },
      { ...queryOptions, enabled: !!id },
    );
    const { items, ...subRes } = res;
    return { ...subRes, item: id ? items[0] : undefined };
  };
