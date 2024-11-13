import { createTheme, ThemeProvider } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import { PropsWithChildren, useMemo } from "react";

type Props = {};
export function JoanieThemeProvider(props: PropsWithChildren<Props>) {
  const themeOptions = useMemo(
    () => ({
      colorSchemes: {
        dark: true,
      },
      width: {
        navigation: 280,
      },
      navigation: {
        width: 280,
      },
    }),
    [],
  );

  const theme = createTheme(themeOptions);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {props.children}
    </ThemeProvider>
  );
}
