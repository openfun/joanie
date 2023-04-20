import * as React from "react";
import { PropsWithChildren, useEffect, useMemo, useState } from "react";
import { IntlProvider } from "react-intl";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import fr from "date-fns/locale/fr";
import enUS from "date-fns/locale/en-US";
import { setLocale } from "yup";
import French from "../../../translations/fr-FR.json";
import { LocalesEnum } from "@/types/i18n/LocalesEnum";

import {
  LocaleContext,
  LocaleContextInterface,
} from "@/contexts/i18n/TranslationsProvider/TranslationContext";
import { useAllLanguages } from "@/hooks/useAllLanguages/useAllLanguages";

interface Props {
  locale: LocalesEnum;
}

export function TranslationsProvider({
  locale = LocalesEnum.ENGLISH,
  ...props
}: PropsWithChildren<Props>) {
  const allLanguages = useAllLanguages();

  const [currentLocale, setCurrentLocale] = useState<LocalesEnum>(locale);
  const [adapterLocale] = useState<Locale>(
    locale !== LocalesEnum.FRENCH ? fr : enUS
  );

  useEffect(() => {}, [allLanguages]);

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
      setCurrentLocale: (newLocale: LocalesEnum) => {
        setCurrentLocale(newLocale);
        setLocale({
          mixed: {
            required: "toto",
          },
        });
      },
    }),
    [currentLocale]
  );

  return (
    <LocaleContext.Provider value={localeContext}>
      <LocalizationProvider
        dateAdapter={AdapterDateFns}
        adapterLocale={adapterLocale}
      >
        <IntlProvider
          locale={locale}
          messages={translations}
          defaultLocale={LocalesEnum.ENGLISH}
        >
          {allLanguages && <div>{props.children}</div>}
        </IntlProvider>
      </LocalizationProvider>
    </LocaleContext.Provider>
  );
}
