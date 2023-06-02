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

interface Props {
  onSelectLang: (lang: string) => void;
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
    return () => {
      localStorage.removeItem(TRANSLATE_CONTENT_LANGUAGE);
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
