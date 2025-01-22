import * as React from "react";
import { PropsWithChildren } from "react";
import { IntlProvider } from "react-intl";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFnsV3";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { enUS } from "date-fns/locale/en-US";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { REACT_QUERY_SETTINGS } from "@/utils/settings";

const client = new QueryClient({
  defaultOptions: {
    queries: {
      gcTime: REACT_QUERY_SETTINGS.cacheTime,
      staleTime: REACT_QUERY_SETTINGS.staleTimes.session,
      ...REACT_QUERY_SETTINGS.queries,
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
