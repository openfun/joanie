import "@/styles/globals.scss";
import { NextPage } from "next";
import { AppProps } from "next/app";
import { useEffect, useState } from "react";
import { CacheProvider } from "@emotion/react";
import createEmotionCache from "@/utils/createEmotionCache";
import { TranslationsProvider } from "@/contexts/i18n/TranslationsProvider/TranslationsProvider";
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
    !(process.env.NEXT_PUBLIC_API_MOCKING === "enabled")
  );

  useEffect(() => {
    async function initMsw() {
      const { initMocks } = await import("../../mocks");
      await initMocks();
      setShouldRender(true);
    }

    if (process.env.NEXT_PUBLIC_API_MOCKING === "enabled") {
      initMsw();
    }
  }, []);

  if (!shouldRender) {
    return null;
  }

  return (
    <TranslationsProvider locale={LocalesEnum.FRENCH}>
      <CacheProvider value={clientSideEmotionCache}>
        <Component {...pageProps} />
      </CacheProvider>
    </TranslationsProvider>
  );
}
