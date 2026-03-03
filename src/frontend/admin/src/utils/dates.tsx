import { getDjangoLang } from "@/utils/lang";

export const formatShortDate = (isoDate: string): string => {
  return new Intl.DateTimeFormat(getDjangoLang(), {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(isoDate));
};
