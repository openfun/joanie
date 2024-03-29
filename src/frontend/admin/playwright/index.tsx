// Import styles, initialize component theme here.
// import '../src/common.css';

import { beforeMount } from "@playwright/experimental-ct-react/hooks";
import { SnackbarProvider } from "notistack";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CacheProvider } from "@emotion/react";
import { IntlProvider } from "react-intl";
import * as React from "react";
import { MemoryRouterProvider } from "next-router-mock/MemoryRouterProvider/next-13.5";
import { JoanieThemeProvider } from "@/theme/JoanieThemeProvider";
import createEmotionCache from "@/utils/createEmotionCache";

export type HooksConfig = {
  customRouting?: boolean;
};

const clientSideEmotionCache = createEmotionCache();
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      gcTime: 24 * 60 * 60 * 1000,
      staleTime: 60 * 1000,
      retry: 0,
      retryOnMount: false,
      refetchOnWindowFocus: false,
    },
  },
});

beforeMount<HooksConfig>(async ({ hooksConfig, App }) => {
  const customRouting = hooksConfig?.customRouting ?? false;
  return (
    <QueryClientProvider client={queryClient}>
      <CacheProvider value={clientSideEmotionCache}>
        <JoanieThemeProvider>
          <SnackbarProvider
            maxSnack={3}
            anchorOrigin={{ horizontal: "right", vertical: "top" }}
          >
            <IntlProvider locale="en-us" defaultLocale="en-us">
              {customRouting ? (
                <App />
              ) : (
                <MemoryRouterProvider url="/">
                  <App />
                </MemoryRouterProvider>
              )}
            </IntlProvider>
          </SnackbarProvider>
        </JoanieThemeProvider>
      </CacheProvider>
    </QueryClientProvider>
  );
});
