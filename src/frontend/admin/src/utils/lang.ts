import cookie from "@boiseitguru/cookie-cutter";
import {
  DJANGO_LANGUAGE_COOKIE_NAME,
  DJANGO_SAVED_LANGUAGE,
  TRANSLATE_CONTENT_LANGUAGE,
} from "@/utils/constants";
import { LocalesEnum } from "@/types/i18n/LocalesEnum";

export const DJANGO_FR_LANG = "fr-fr";
export const DJANGO_EN_LANG = "en-us";

export enum DjangoLangEnum {
  FR = DJANGO_FR_LANG,
  EN = DJANGO_EN_LANG,
}
export const ALL_DJANGO_LANG: string[] = [DjangoLangEnum.FR, DjangoLangEnum.EN];

export const getDefaultLang = (): string => {
  return process.env.NEXT_PUBLIC_LANG ?? DJANGO_EN_LANG;
};

export const getDjangoLang = (): string => {
  return cookie.get(DJANGO_LANGUAGE_COOKIE_NAME) ?? getDefaultLang();
};

export const deleteDjangoLang = (): string => {
  const old = getDjangoLang();
  localStorage.setItem(DJANGO_SAVED_LANGUAGE, old);
  const expiredDate = new Date(0);
  cookie.set(DJANGO_LANGUAGE_COOKIE_NAME, "", {
    path: "/",
    expires: expiredDate,
  });
  return old;
};

export const setDjangoLang = (lang: string) => {
  const newLang = ALL_DJANGO_LANG.includes(lang) ? lang : getDefaultLang();
  if (localStorage.getItem(TRANSLATE_CONTENT_LANGUAGE)) {
    setSavedDjangoLanguage(newLang);
    return;
  }
  localStorage.removeItem(DJANGO_SAVED_LANGUAGE);
  cookie.set(DJANGO_LANGUAGE_COOKIE_NAME, newLang, { path: "/" });
};

export const setDjangoLangFromLocale = (newLocale: LocalesEnum) => {
  const newLang =
    newLocale === LocalesEnum.FRENCH ? DjangoLangEnum.FR : DjangoLangEnum.EN;
  if (localStorage.getItem(TRANSLATE_CONTENT_LANGUAGE)) {
    setSavedDjangoLanguage(newLang);
    return;
  }
  cookie.set(DJANGO_LANGUAGE_COOKIE_NAME, newLang, { path: "/" });
};

export const getLocaleFromDjangoLang = (djangoLang?: string): LocalesEnum => {
  const lang = djangoLang ?? getDjangoLang();
  return lang === DJANGO_FR_LANG ? LocalesEnum.FRENCH : LocalesEnum.ENGLISH;
};

export const getSavedDjangoLanguage = (): string => {
  return localStorage.getItem(DJANGO_SAVED_LANGUAGE) + "" ?? "";
};

export const setSavedDjangoLanguage = (lang: string): void => {
  localStorage.setItem(DJANGO_SAVED_LANGUAGE, lang);
};
