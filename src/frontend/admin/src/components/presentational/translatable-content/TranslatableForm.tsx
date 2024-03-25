import * as React from "react";
import { PropsWithChildren, useEffect, useMemo, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import { TabContext } from "@mui/lab";
import { useTheme } from "@mui/material/styles";
import { TRANSLATE_CONTENT_LANGUAGE } from "@/utils/constants";
import { LocalesEnum } from "@/types/i18n/LocalesEnum";
import { getAcceptLanguage } from "@/services/http/HttpService";
import { getLocaleFromDjangoLang } from "@/utils/lang";
import { Maybe } from "@/types/utils";

interface Props {
  onSelectLang: (lang?: string) => void;
  entitiesDeps?: any[];
  resetForm?: () => void;
}

export function TranslatableForm({
  entitiesDeps,
  resetForm,
  ...props
}: PropsWithChildren<Props>) {
  const langHasChanged = useRef<boolean>(false);
  const formHasBeenReset = useRef<boolean>(false);
  const [value, setValue] = useState(getAcceptLanguage());
  const theme = useTheme();

  const a11yProps = (index: number) => {
    return {
      id: `translate-tab-${index}`,
      "aria-controls": `translate-tabpanel-${index}`,
    };
  };

  const handleChange = (event: React.SyntheticEvent, newValue: string) => {
    if (value === newValue) {
      return;
    }
    setValue(newValue);
    localStorage.setItem(TRANSLATE_CONTENT_LANGUAGE, newValue);
    langHasChanged.current = true;
    props.onSelectLang(newValue);
  };

  useEffect(() => {
    if (langHasChanged.current) {
      langHasChanged.current = false;
      if (resetForm) {
        resetForm();
        formHasBeenReset.current = true;
      }
    }
  }, entitiesDeps);

  useEffect(() => {
    localStorage.setItem(TRANSLATE_CONTENT_LANGUAGE, getLocaleFromDjangoLang());
    const oldOnbeforeunload = window.onbeforeunload;
    /*
      The translation of content and the retrieval of an object according to a given language are done via the same
      header on a GET / POST request. We play on the priorities in the "getAcceptLanguage" method of HttpService.
      We add this event because if we are on a page with translatable content, we need to reset the
      TRANSLATE_CONTENT_LANGUAGE key in localStorage when we leave or refresh the page so that the object is retrieved
      in the current language and not in the current language forced. by the TranslatableContent component
     */
    window.onbeforeunload = () => {
      localStorage.removeItem(TRANSLATE_CONTENT_LANGUAGE);
    };
    return () => {
      window.onbeforeunload = oldOnbeforeunload;
      localStorage.removeItem(TRANSLATE_CONTENT_LANGUAGE);
      props.onSelectLang(getLocaleFromDjangoLang());
    };
  }, []);

  const contextValue: TranslatableFormContextInterface = useMemo(
    () => ({
      langHasChange: langHasChanged.current,
      formHasBeenReset: formHasBeenReset.current,
      setFormHasBeenRest: (b: boolean) => (formHasBeenReset.current = b),
    }),
    [langHasChanged.current, formHasBeenReset.current],
  );

  return (
    <TranslatableFormContext.Provider value={contextValue}>
      <TabContext value={value}>
        <Box
          mb={2}
          sx={{
            backgroundColor: theme.palette.grey[50],
          }}
        >
          <Tabs
            value={value}
            onChange={handleChange}
            aria-label="basic tabs example"
          >
            <Tab
              label="English"
              value={LocalesEnum.ENGLISH}
              {...a11yProps(0)}
            />
            <Tab label="French" value={LocalesEnum.FRENCH} {...a11yProps(1)} />
          </Tabs>
        </Box>
        <Box p={3}>{props.children}</Box>
      </TabContext>
    </TranslatableFormContext.Provider>
  );
}

export interface TranslatableFormContextInterface {
  langHasChange: boolean;
  formHasBeenReset: boolean;
  setFormHasBeenRest: (hasBeenReset: boolean) => void;
}

export const TranslatableFormContext =
  React.createContext<Maybe<TranslatableFormContextInterface>>(undefined);

export const useTranslatableFormContext = () => {
  const context = React.useContext(TranslatableFormContext);

  if (context) {
    return context;
  }

  return null;
};
