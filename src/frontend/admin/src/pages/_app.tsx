import "@/styles/globals.scss";
import type { AppProps } from "next/app";
import { CacheProvider } from "@emotion/react";
import "@fontsource/roboto/300.css";
import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/roboto/700.css";
import { NextPage } from "next";
import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Box, CircularProgress } from "@mui/material";
import { SnackbarProvider } from "notistack";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import createEmotionCache from "@/utils/createEmotionCache";
import { DashboardLayout } from "@/layouts/dashboard/DashboardLayout";

import { LocalesEnum } from "@/types/i18n/LocalesEnum";
import { TranslationsProvider } from "@/contexts/i18n/TranslationsProvider/TranslationsProvider";
import { REACT_QUERY_SETTINGS } from "@/utils/settings";

type NextPageWithLayout = NextPage & {
  getLayout?: (page: React.ReactElement) => React.ReactNode;
};

interface MyAppProps extends AppProps {
  Component: NextPageWithLayout;
}

const clientSideEmotionCache = createEmotionCache();

export default function App({ Component, pageProps }: MyAppProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            cacheTime: REACT_QUERY_SETTINGS.cacheTime,
            staleTime: 60 * 1000, // 1 mi
            retry: 0,
            retryOnMount: false,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  const [shouldRender, setShouldRender] = useState(
    !(process.env.NEXT_PUBLIC_API_MOCKING === "enabled")
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

    if (process.env.NEXT_PUBLIC_API_MOCKING === "enabled") {
      initMsw();
    }
  }, []);

  if (!shouldRender) {
    return (
      <Box
        position="absolute"
        left={0}
        right={0}
        top={0}
        bottom={0}
        display="flex"
        justifyContent="center"
        alignItems="center"
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <ReactQueryDevtools initialIsOpen={false} />
      <TranslationsProvider locale={LocalesEnum.ENGLISH}>
        <CacheProvider value={clientSideEmotionCache}>
          <SnackbarProvider
            maxSnack={3}
            anchorOrigin={{ horizontal: "right", vertical: "top" }}
          >
            {getLayout(<Component {...pageProps} />)}
          </SnackbarProvider>
        </CacheProvider>
      </TranslationsProvider>
    </QueryClientProvider>
  );
}
