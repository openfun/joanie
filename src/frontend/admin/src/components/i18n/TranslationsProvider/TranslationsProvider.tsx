import * as React from "react";
import { PropsWithChildren, useEffect, useMemo, useState } from "react";
import { IntlProvider, MessageFormatElement } from "react-intl";
import French from "../../../translations/fr-FR.json";
import { LocalesEnum } from "@/types/i18n/LocalesEnum";
import {
  LocaleContext,
  LocaleContextInterface,
} from "@/components/i18n/TranslationsProvider/TranslationContext";

import { Maybe } from "@/types/utils";

interface Props {
  locale: LocalesEnum;
}

export function TranslationsProvider({
  locale = LocalesEnum.ENGLISH,
  ...props
}: PropsWithChildren<Props>) {
  const [currentLocale, setCurrentLocale] = useState<LocalesEnum>(locale);
  const [translations, setTranslations] =
    useState<
      Maybe<Record<string, string> | Record<string, MessageFormatElement[]>>
    >(undefined);

  const updateLocale = (newLocale: string): void => {
    switch (newLocale) {
      case LocalesEnum.FRENCH:
        setTranslations(French);
        break;
      default:
        setTranslations(undefined);
        break;
    }
  };

  const localeContext: LocaleContextInterface = useMemo(
    () => ({
      currentLocale,
      setCurrentLocale: (newLocale: LocalesEnum) => {
        setCurrentLocale(newLocale);
        updateLocale(newLocale);
      },
    }),
    [currentLocale]
  );

  useEffect(() => {
    updateLocale(locale);
  }, [locale]);

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
