import { Nullable } from "./utils";

export interface PaginatedResponse<T> {
  count: number;
  next: Nullable<string>;
  previous: Nullable<string>;
  results: Array<T>;
}
