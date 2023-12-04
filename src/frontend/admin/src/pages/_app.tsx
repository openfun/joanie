import "@/styles/globals.scss";
import type { AppProps } from "next/app";
import "@uiw/react-md-editor/markdown-editor.css";
// eslint-disable-next-line import/no-extraneous-dependencies
import "@uiw/react-markdown-preview/markdown.css";
import { CacheProvider } from "@emotion/react";
import "@fontsource/roboto/300.css";
import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/roboto/700.css";
import { NextPage } from "next";
import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";
import { SnackbarProvider } from "notistack";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useTheme } from "@mui/material/styles";
import createEmotionCache from "@/utils/createEmotionCache";
import { DashboardLayout } from "@/layouts/dashboard/DashboardLayout";

import { LocalesEnum } from "@/types/i18n/LocalesEnum";
import { TranslationsProvider } from "@/contexts/i18n/TranslationsProvider/TranslationsProvider";
import { REACT_QUERY_SETTINGS } from "@/utils/settings";
import { JoanieThemeProvider } from "@/theme/JoanieThemeProvider";
import { AuthProvider } from "@/contexts/auth/AuthProvider";

type NextPageWithLayout = NextPage & {
  getLayout?: (page: React.ReactElement) => React.ReactNode;
};

interface MyAppProps extends AppProps {
  Component: NextPageWithLayout;
}

const clientSideEmotionCache = createEmotionCache();

export default function App({ Component, pageProps }: MyAppProps) {
  const theme = useTheme();
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            gcTime: REACT_QUERY_SETTINGS.cacheTime,
            staleTime: 60 * 1000, // 1 mi
            retry: 0,
            retryOnMount: false,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  const [shouldRender, setShouldRender] = useState(
    !(process.env.NEXT_PUBLIC_API_SOURCE === "mocked"),
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
    return (
      <Box
        sx={{ inset: 0 }}
        position="absolute"
        display="flex"
        justifyContent="center"
        alignItems="center"
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <AuthProvider>
      <QueryClientProvider client={queryClient}>
        <ReactQueryDevtools initialIsOpen={false} />
        <TranslationsProvider locale={LocalesEnum.ENGLISH}>
          <CacheProvider value={clientSideEmotionCache}>
            <JoanieThemeProvider>
              <SnackbarProvider
                style={{
                  fontFamily: theme.typography.fontFamily,
                }}
                maxSnack={3}
                anchorOrigin={{ horizontal: "right", vertical: "top" }}
              >
                {getLayout(<Component {...pageProps} />)}
              </SnackbarProvider>
            </JoanieThemeProvider>
          </CacheProvider>
        </TranslationsProvider>
      </QueryClientProvider>
    </AuthProvider>
  );
}
