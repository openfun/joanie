import "@/styles/globals.scss";
import type { AppProps } from "next/app";

import { CacheProvider } from "@emotion/react";
import "@fontsource/roboto/300.css";
import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/roboto/700.css";
import { NextPage } from "next";
import { useEffect, useState } from "react";
import { Experimental_CssVarsProvider as CssVarsProvider } from "@mui/material/styles";
import createEmotionCache from "@/utils/createEmotionCache";
import { DashboardLayout } from "@/layouts/dashboard/DashboardLayout";

import { TranslationsProvider } from "@/components/i18n/TranslationsProvider/TranslationsProvider";
import { LocalesEnum } from "@/types/i18n/LocalesEnum";

type NextPageWithLayout = NextPage & {
  getLayout?: (page: React.ReactElement) => React.ReactNode;
};

interface MyAppProps extends AppProps {
  Component: NextPageWithLayout;
}

const clientSideEmotionCache = createEmotionCache();

export default function App({ Component, pageProps }: MyAppProps) {
  const [shouldRender, setShouldRender] = useState(
    !(process.env.NEXT_PUBLIC_API_SOURCE === "mocked")
  );

  const getLayout =
    Component.getLayout ??
    ((page) => <DashboardLayout>{page}</DashboardLayout>);

  useEffect(() => {
    async function initMsw() {
      const { initMocks } = await import("../../mocks");
      await initMocks();
      setShouldRender(true);
    }

    if (process.env.NEXT_PUBLIC_API_SOURCE === "mocked") {
      initMsw();
    }
  }, []);

  if (!shouldRender) {
    return null;
  }

  return (
    <TranslationsProvider locale={LocalesEnum.ENGLISH}>
      <CacheProvider value={clientSideEmotionCache}>
        <CssVarsProvider>
          {getLayout(<Component {...pageProps} />)}
        </CssVarsProvider>
      </CacheProvider>
    </TranslationsProvider>
  );
}
