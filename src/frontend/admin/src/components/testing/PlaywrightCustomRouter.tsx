import * as React from "react";
import { PropsWithChildren } from "react";
import { MemoryRouter } from "next-router-mock";
import { MemoryRouterProvider } from "next-router-mock/MemoryRouterProvider/next-13.5";

type Props = {
  initialUrl?: string;
  router: MemoryRouter;
};
export function PlaywrightCustomRouter({
  initialUrl = "/",
  router,
  children,
}: PropsWithChildren<Props>) {
  return (
    <MemoryRouterProvider
      url={initialUrl}
      onPush={async (url, options) => {
        await router.push(url, undefined, options);
      }}
    >
      {children}
    </MemoryRouterProvider>
  );
}
