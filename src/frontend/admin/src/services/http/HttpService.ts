// eslint-disable-next-line import/no-extraneous-dependencies
import Cookies from "js-cookie";
import { HttpError } from "@/services/http/HttpError";
import {
  INTERFACE_USER_LANGUAGE,
  TRANSLATE_CONTENT_LANGUAGE,
} from "@/utils/constants";
import { LocalesEnum } from "@/types/i18n/LocalesEnum";

export const fetchApi = (routes: RequestInfo, options: RequestInit = {}) => {
  const headers =
    (options.headers as Record<string, string>) || getDefaultHeaders();

  const csrf = Cookies.get("csrftoken");
  if (csrf) {
    headers["X-CSRFToken"] = csrf;
  }

  options.headers = headers;
  options.credentials = "include";

  return fetch(buildApiUrl(routes), options);
};

export const getAcceptLanguage = (): string => {
  const translateContent = localStorage.getItem(TRANSLATE_CONTENT_LANGUAGE);
  const interfaceLang = localStorage.getItem(INTERFACE_USER_LANGUAGE);

  if (translateContent) {
    return translateContent;
  } else if (interfaceLang) {
    return interfaceLang;
  }

  return LocalesEnum.FRENCH;
};

function getDefaultHeaders(): Record<string, string> {
  const language = getAcceptLanguage();

  return {
    // "Content-Type": "application/json",
    "Accept-Language": language,
  };
}

export const buildApiUrl = (route: RequestInfo) => {
  return `${process.env.NEXT_PUBLIC_API_ENDPOINT}${route}`;
};

interface CheckStatusOptions {
  fallbackValue: any;
  ignoredErrorStatus: number[];
}

export async function checkStatus(
  response: Response,
  options: CheckStatusOptions = { fallbackValue: null, ignoredErrorStatus: [] }
): Promise<any> {
  if (response.ok) {
    if (response.headers.get("Content-Type") === "application/json") {
      return response.json();
    }
    if (response.headers.get("Content-Type") === "application/pdf") {
      return response.blob();
    }
    return response.text();
  }

  if (options.ignoredErrorStatus.includes(response.status)) {
    return Promise.resolve(options.fallbackValue);
  }

  const data = await response.json();

  throw new HttpError(response.status, response.statusText, data);
}
