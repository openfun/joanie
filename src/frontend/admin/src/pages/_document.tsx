import { Head, Html, Main, NextScript } from "next/document";
import { getInitColorSchemeScript } from "@mui/material";

export default function Document() {
  return (
    <Html lang="en">
      <Head />
      <body>
        {getInitColorSchemeScript()}
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
