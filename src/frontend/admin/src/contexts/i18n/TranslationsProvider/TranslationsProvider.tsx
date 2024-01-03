import * as React from "react";
import { PropsWithChildren, useMemo, useState } from "react";
import { IntlProvider } from "react-intl";
import { LocalizationProvider } from "@mui/x-date-pickers";

import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import fr from "date-fns/locale/fr";
import enUS from "date-fns/locale/en-US";
import { useQueryClient } from "@tanstack/react-query";
import French from "@/translations/fr-FR.json";
import { LocalesEnum } from "@/types/i18n/LocalesEnum";
import {
  LocaleContext,
  LocaleContextInterface,
} from "@/contexts/i18n/TranslationsProvider/TranslationContext";
import { useAllLanguages } from "@/hooks/useAllLanguages/useAllLanguages";
import { getLocaleFromDjangoLang, setDjangoLangFromLocale } from "@/utils/lang";

export function TranslationsProvider({ children }: PropsWithChildren<{}>) {
  const queryClient = useQueryClient();
  const defaultLocal = getLocaleFromDjangoLang();
  const allLanguages = useAllLanguages();
  const [currentLocale, setCurrentLocale] = useState<LocalesEnum>(defaultLocal);
  const [adapterLocale] = useState<Locale>(
    defaultLocal !== LocalesEnum.FRENCH ? fr : enUS,
  );

  const translations = useMemo(() => {
    switch (currentLocale) {
      case LocalesEnum.FRENCH:
        return French;
      default:
        return undefined;
    }
  }, [currentLocale]);

  const localeContext: LocaleContextInterface = useMemo(
    () => ({
      currentLocale,
      setCurrentLocale: async (newLocale: LocalesEnum) => {
        setCurrentLocale(newLocale);
        setDjangoLangFromLocale(newLocale);
        await queryClient.invalidateQueries();
      },
    }),
    [currentLocale],
  );

  return (
    <LocaleContext.Provider value={localeContext}>
      <LocalizationProvider
        dateAdapter={AdapterDateFns}
        adapterLocale={adapterLocale}
      >
        <IntlProvider
          locale={currentLocale}
          messages={translations}
          defaultLocale={LocalesEnum.ENGLISH}
        >
          {allLanguages && <div>{children}</div>}
        </IntlProvider>
      </LocalizationProvider>
    </LocaleContext.Provider>
  );
}
