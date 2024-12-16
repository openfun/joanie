import { Maybe, Nullable } from "@/types/utils";

export const removeEOL = (str: Maybe<Nullable<string>>): string => {
  if (!str) {
    return "";
  }
  return str?.replace(/(\r)/gm, "");
};
