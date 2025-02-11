import { QueryKey, UseQueryOptions } from "@tanstack/react-query";
import { HttpError } from "@/services/http/HttpError";

export interface Resource {
  id?: string;
}

export interface ResourcesQuery {
  ids?: string[];
  id?: string;
  query?: string;
  page?: number;
  ordering?: string;
}

export type QueryOptions<TData extends Resource> = Omit<
  UseQueryOptions<unknown, HttpError, TData[]>,
  "queryKey" | "queryFn"
>;

export interface ApiResourceInterface<
  TData extends Resource,
  TResourceQuery extends ResourcesQuery = ResourcesQuery,
> {
  get: (filters?: TResourceQuery) => any;
  create?: (payload: any) => Promise<TData>;
  update?: (payload: any) => Promise<TData>;
  delete?: (id: TData["id"]) => Promise<void>;
  export?: (filters?: TResourceQuery) => Promise<void>;
}

export const useLocalizedQueryKey = (queryKey: QueryKey) => queryKey;
