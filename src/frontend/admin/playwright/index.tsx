// Import styles, initialize component theme here.
// import '../src/common.css';

import { beforeMount } from "@playwright/experimental-ct-react/hooks";
import { SnackbarProvider } from "notistack";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CacheProvider } from "@emotion/react";
import { JoanieThemeProvider } from "@/theme/JoanieThemeProvider";
import createEmotionCache from "@/utils/createEmotionCache";

const clientSideEmotionCache = createEmotionCache();
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      gcTime: 24 * 60 * 60 * 1000,
      staleTime: 60 * 1000, // 1 mi
      retry: 0,
      retryOnMount: false,
      refetchOnWindowFocus: false,
    },
  },
});

beforeMount(async ({ App }) => {
  return (
    <QueryClientProvider client={queryClient}>
      <CacheProvider value={clientSideEmotionCache}>
        <JoanieThemeProvider>
          <SnackbarProvider
            maxSnack={3}
            anchorOrigin={{ horizontal: "right", vertical: "top" }}
          >
            <App />
          </SnackbarProvider>
        </JoanieThemeProvider>
      </CacheProvider>
    </QueryClientProvider>
  );
});
