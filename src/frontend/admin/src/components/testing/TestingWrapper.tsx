import * as React from "react";
import { PropsWithChildren } from "react";
import { IntlProvider } from "react-intl";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider } from "@mui/x-date-pickers";
import enUS from "date-fns/locale/en-US";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { REACT_QUERY_SETTINGS } from "@/utils/settings";

const client = new QueryClient({
  defaultOptions: {
    queries: {
      cacheTime: REACT_QUERY_SETTINGS.cacheTime,
      staleTime: 60 * 1000, // 1 mi
      retry: 0,
      retryOnMount: false,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
    },
  },
});

export function TestingWrapper(props: PropsWithChildren) {
  return (
    <QueryClientProvider client={client}>
      <IntlProvider locale="en">
        <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={enUS}>
          {props.children}
        </LocalizationProvider>
      </IntlProvider>
    </QueryClientProvider>
  );
}
