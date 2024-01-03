import * as process from "process";
import cookie from "@boiseitguru/cookie-cutter";
import { DJANGO_LANGUAGE_COOKIE_NAME } from "@/utils/constants";
import { LocalesEnum } from "@/types/i18n/LocalesEnum";

export const DJANGO_FR_LANG = "fr";
export const DJANGO_EN_LANG = "en";
export enum DjangoLangEnum {
  FR = "fr",
  EN = "en",
}
export const ALL_DJANGO_LANG: string[] = [DjangoLangEnum.FR, DjangoLangEnum.EN];

export const getDjangoLang = (): string => {
  const envDefaultLang = process.env.NEXT_PUBLIC_LANG ?? DJANGO_EN_LANG;
  return cookie.get(DJANGO_LANGUAGE_COOKIE_NAME) ?? envDefaultLang;
};

export const setDjangoLang = (lang: string) => {
  const newLang = ALL_DJANGO_LANG.includes(lang) ? lang : DJANGO_FR_LANG;
  cookie.set(DJANGO_LANGUAGE_COOKIE_NAME, newLang);
};

export const setDjangoLangFromLocale = (newLocale: LocalesEnum) => {
  const newLang = newLocale === LocalesEnum.FRENCH ? "fr" : "en";
  cookie.set(DJANGO_LANGUAGE_COOKIE_NAME, newLang);
};

export const getLocaleFromDjangoLang = (djangoLang?: string): LocalesEnum => {
  const lang = djangoLang ?? getDjangoLang();
  return lang === DJANGO_FR_LANG ? LocalesEnum.FRENCH : LocalesEnum.ENGLISH;
};
