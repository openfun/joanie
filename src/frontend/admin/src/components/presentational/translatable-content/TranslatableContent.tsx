import * as React from "react";
import { PropsWithChildren, useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import { TabContext } from "@mui/lab";
import { useTheme } from "@mui/material/styles";
import { TRANSLATE_CONTENT_LANGUAGE } from "@/utils/constants";
import { LocalesEnum } from "@/types/i18n/LocalesEnum";
import { getAcceptLanguage } from "@/services/http/HttpService";
import { getLocaleFromDjangoLang } from "@/utils/lang";

interface Props {
  onSelectLang: (lang?: string) => void;
}

export function TranslatableContent({ ...props }: PropsWithChildren<Props>) {
  const [value, setValue] = useState(getAcceptLanguage());
  const theme = useTheme();

  const a11yProps = (index: number) => {
    return {
      id: `translate-tab-${index}`,
      "aria-controls": `translate-tabpanel-${index}`,
    };
  };

  const handleChange = (event: React.SyntheticEvent, newValue: string) => {
    setValue(newValue);
    localStorage.setItem(TRANSLATE_CONTENT_LANGUAGE, newValue);
    props.onSelectLang(newValue);
  };
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

  return (
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
          <Tab label="English" value={LocalesEnum.ENGLISH} {...a11yProps(0)} />
          <Tab label="French" value={LocalesEnum.FRENCH} {...a11yProps(1)} />
        </Tabs>
      </Box>
      {props.children}
    </TabContext>
  );
}
