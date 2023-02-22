import "@/styles/globals.scss";
import type { AppProps } from "next/app";
import { CacheProvider } from "@emotion/react";
import "@fontsource/roboto/300.css";
import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/roboto/700.css";
import { NextPage } from "next";
import createEmotionCache from "@/utils/createEmotionCache";

type NextPageWithLayout = NextPage & {
  getLayout?: (page: React.ReactElement) => React.ReactNode;
};

interface MyAppProps extends AppProps {
  Component: NextPageWithLayout;
}

const clientSideEmotionCache = createEmotionCache();

export default function App({ Component, pageProps }: MyAppProps) {
  return (
    <CacheProvider value={clientSideEmotionCache}>
      <Component {...pageProps} />
    </CacheProvider>
  );
}
