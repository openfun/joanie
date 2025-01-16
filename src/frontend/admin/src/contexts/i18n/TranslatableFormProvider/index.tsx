import {
  PropsWithChildren,
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  deleteDjangoLang,
  getSavedDjangoLanguage,
  setDjangoLang,
} from "@/utils/lang";
import { TRANSLATE_CONTENT_LANGUAGE } from "@/utils/constants";
import usePrevious from "@/hooks/usePrevious";

const TranslatableFormContext = createContext({
  register: () => {},
  unregister: () => {},
  registeredForms: 0,
});

/**
 * The TranslatableFormProvider aims to monitor the use of TranslatableForms.
 * Actually, we need to be sure that there is no TranslatableForm mounted in the page
 * to restore the cookie `django_language` to its previous value. Otherwise, we manage
 * locale settings in the local storage to not send locale information in the headers through
 * cookies as if this the case, the Django middleware in charge to activate the locale will give
 * priority to the cookie value over the header `Accept-Language`...
 *
 * So this provider registers all TranslableForms mounted and when last one is unmounted, it is
 * in charge to restore the cookie `django_language` to its previous value.
 */
function TranslatableFormProvider({ children }: PropsWithChildren<{}>) {
  const [registeredForms, setRegisteredForms] = useState<number>(0);
  const previousRegisteredForms = usePrevious(registeredForms);
  const register = () => {
    setRegisteredForms((prev) => prev + 1);
  };
  const unregister = () => {
    setRegisteredForms((prev) => Math.max(0, prev - 1));
  };

  const context = useMemo(
    () => ({ register, unregister, registeredForms }),
    [register, unregister, registeredForms],
  );

  useEffect(() => {
    // A first TranslatableForm has been mounted, we remove the cookie `django_language`
    // and save its value in the local storage
    if (previousRegisteredForms === 0 && registeredForms > 0) {
      const old = deleteDjangoLang();
      localStorage.setItem(TRANSLATE_CONTENT_LANGUAGE, old);

      const resetTranslateContentLanguage = () => {
        const oldDjangoLanguage = getSavedDjangoLanguage();
        if (oldDjangoLanguage) {
          localStorage.removeItem(TRANSLATE_CONTENT_LANGUAGE);
          setDjangoLang(oldDjangoLanguage);
        }
      };

      /*
      The translation of content and the retrieval of an object according to a given language are done via the same
      header on a GET / POST request. We play on the priorities in the "getAcceptLanguage" method of HttpService.
      We add this event because if we are on a page with translatable content, we need to reset the
      TRANSLATE_CONTENT_LANGUAGE key in localStorage when we leave or refresh the page so that the object is retrieved
      in the current language and not in the current language forced. by the TranslatableContent component
     */
      window.addEventListener("beforeunload", resetTranslateContentLanguage, {
        once: true,
      });

      return () => {
        window.removeEventListener(
          "beforeunload",
          resetTranslateContentLanguage,
        );
      };
    }

    // The last TranslatableForm has been unmounted, we restore the cookie `django_language`
    if (previousRegisteredForms > 0 && registeredForms === 0) {
      const oldDjangoLanguage = getSavedDjangoLanguage();
      localStorage.removeItem(TRANSLATE_CONTENT_LANGUAGE);
      setDjangoLang(oldDjangoLanguage);
    }
  }, [registeredForms]);

  return (
    <TranslatableFormContext.Provider value={context}>
      {children}
    </TranslatableFormContext.Provider>
  );
}

export const useTranslatableForm = () => {
  return useContext(TranslatableFormContext);
};

export default TranslatableFormProvider;
