import { getDjangoLang } from "@/utils/lang";
import { isTestEnv } from "@/utils/testing";

export const formatShortDate = (isoDate: string): string => {
  return new Intl.DateTimeFormat(getDjangoLang(), {
    dateStyle: "short",
    timeStyle: "short",
    ...(isTestEnv() ? { timeZone: "UTC" } : {}),
  }).format(new Date(isoDate));
};
