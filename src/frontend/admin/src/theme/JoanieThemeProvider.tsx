// @flow
import { createTheme, ThemeOptions, ThemeProvider } from "@mui/material/styles";
import * as React from "react";
import { PropsWithChildren, useMemo } from "react";

type Props = {};
export function JoanieThemeProvider(props: PropsWithChildren<Props>) {
  const themeOptions: ThemeOptions = useMemo(
    () => ({
      width: {
        navigation: 280,
      },
      navigation: {
        width: 280,
      },
    }),
    []
  );

  const theme = createTheme(themeOptions);

  return <ThemeProvider theme={theme}>{props.children}</ThemeProvider>;
}
