import { QueryKey } from "@tanstack/react-query";

export interface Resource {
  id?: string;
}

export interface ResourcesQuery {
  id?: string;
}

export interface ApiResourceInterface<
  TData extends Resource,
  TResourceQuery extends ResourcesQuery = ResourcesQuery
> {
  get: (filters?: TResourceQuery) => any;
  create?: (payload: any) => Promise<TData>;
  update?: (payload: any) => Promise<TData>;
  delete?: (id: TData["id"]) => Promise<void>;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  prev: string | null;
  results: Array<T>;
}

export const useLocalizedQueryKey = (queryKey: QueryKey) => queryKey;
