import * as React from "react";
import { PropsWithChildren } from "react";
import { useRouter } from "next/router";
import Box from "@mui/material/Box";
import { useAuthContext } from "@/components/auth/context/AuthContext";

type Props = {};
export function AuthGuard(props: PropsWithChildren<Props>) {
  const { user } = useAuthContext();
  const router = useRouter();

  if (!user) {
    router.push("/auth/login");
    return null;
  }

  return <Box height="100%">{props.children}</Box>;
}
