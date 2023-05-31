import { ResourcesQuery } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";

export interface AbstractRepository<
  T,
  Filters extends ResourcesQuery,
  DTOData
> {
  getAll: (filters?: Maybe<Filters>) => Promise<T[]>;

  get: (id: string, filters?: Maybe<Filters>) => Promise<T>;

  create: (payload: DTOData) => Promise<T>;

  update: (id: string, payload: DTOData) => Promise<T>;

  delete: (id: string) => Promise<void>;
}
