import * as React from "react";
import { PropsWithChildren } from "react";
import { Link, LinkProps } from "@mui/material";
import NextLink from "next/link";

type Props = LinkProps;
export function CustomLink({ children, ...props }: PropsWithChildren<Props>) {
  return (
    <Link
      underline="hover"
      key={props.href}
      component={NextLink}
      color="inherit"
      {...props}
    >
      {children}
    </Link>
  );
}
