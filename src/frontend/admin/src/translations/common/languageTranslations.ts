import { defineMessages } from "react-intl";
import { LocalesEnum } from "@/types/i18n/LocalesEnum";

export const languageTranslations = defineMessages<LocalesEnum>({
  [LocalesEnum.ENGLISH]: {
    id: "translations.common.languageTranslations.english",
    defaultMessage: "English",
    description: "Common english label",
  },
  [LocalesEnum.FRENCH]: {
    id: "translations.common.languageTranslations.french",
    defaultMessage: "French",
    description: "Common french label",
  },
});
