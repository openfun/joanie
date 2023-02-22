import React from "react";
import { Maybe } from "@/types/utils";
import { LocalesEnum } from "@/types/i18n/LocalesEnum";

export interface LocaleContextInterface {
  currentLocale: string;
  setCurrentLocale: (locale: LocalesEnum) => void;
}

export const LocaleContext =
  React.createContext<Maybe<LocaleContextInterface>>(undefined);

export const useLocale = () => {
  const localContext = React.useContext(LocaleContext);

  if (localContext) {
    return localContext;
  }

  throw new Error(`useLocale must be used within a LocaleContext`);
};
