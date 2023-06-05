export {};
declare module "@mui/material/styles" {
  interface Theme {
    navigation: {
      width: number;
    };
  }
  // allow configuration using `createTheme`
  interface ThemeOptions {
    navigation?: {
      width: number;
    };
  }
}
