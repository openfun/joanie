import * as React from "react";
import { PropsWithChildren, useMemo, useState } from "react";
import { IntlProvider } from "react-intl";
import French from "@/translations/fr-FR.json";
import { LocalesEnum } from "@/types/i18n/LocalesEnum";
import {
  LocaleContext,
  LocaleContextInterface,
} from "@/contexts/i18n/TranslationsProvider/TranslationContext";

interface Props {
  locale: LocalesEnum;
}

export function TranslationsProvider({
  locale = LocalesEnum.ENGLISH,
  ...props
}: PropsWithChildren<Props>) {
  const [currentLocale, setCurrentLocale] = useState<LocalesEnum>(locale);

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
      },
    }),
    [currentLocale]
  );

  return (
    <LocaleContext.Provider value={localeContext}>
      <IntlProvider
        locale={locale}
        messages={translations}
        defaultLocale={LocalesEnum.ENGLISH}
      >
        {props.children}
      </IntlProvider>
    </LocaleContext.Provider>
  );
}
