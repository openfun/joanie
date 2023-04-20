import { FieldPath } from "react-hook-form/dist/types/path";
import { FieldValues } from "react-hook-form/dist/types/fields";

export type Maybe<T> = T | undefined;

export type Nullable<T> = T | null;

export type AddParameters<
  TFunction extends (...args: readonly unknown[]) => unknown,
  TParameters extends [...args: readonly unknown[]]
> = (
  ...args: [...Parameters<TFunction>, ...TParameters]
) => ReturnType<TFunction>;

export type ServerSideErrorForm<T extends FieldValues> = Record<
  FieldPath<T>,
  string[]
>;
