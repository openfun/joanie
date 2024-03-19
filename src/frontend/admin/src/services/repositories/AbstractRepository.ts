import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe, Nullable } from "@/types/utils";

export type PaginatedResponse<T> = {
  count: number;
  next: Nullable<number>;
  previous: Nullable<number>;
  results: T[];
};

export interface AbstractRepository<
  T,
  Filters extends ResourcesQuery,
  DTOData,
> {
  getAll: (filters?: Maybe<Filters>) => Promise<PaginatedResponse<T>>;

  get: (id: string, filters?: Maybe<Filters>) => Promise<T>;

  create: (payload: DTOData) => Promise<T>;

  update: (id: string, payload: DTOData) => Promise<T>;

  delete: (id: string) => Promise<void>;
}
