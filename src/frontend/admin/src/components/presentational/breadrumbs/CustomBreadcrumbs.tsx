import * as React from "react";
import Box from "@mui/material/Box";
import Breadcrumbs from "@mui/material/Breadcrumbs";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import { BreadcrumbsLinkProps } from "@/components/presentational/breadrumbs/type";

interface Props {
  links: BreadcrumbsLinkProps[];
}

export function CustomBreadcrumbs({ links }: Props) {
  return (
    <Breadcrumbs
      separator={
        <Box
          aria-label="breadcrumb-separator"
          sx={{
            backgroundColor: "rgb(108, 115, 127)",
            width: "4px",
            height: "4px",
            borderRadius: "50%",
          }}
        />
      }
      sx={{ my: 1 }}
      aria-label="breadcrumb"
    >
      {links.map((linkItem) =>
        linkItem.href ? (
          <Link
            underline="hover"
            key={linkItem.href}
            component={NextLink}
            color="inherit"
            href={linkItem.href}
          >
            {linkItem.name}
          </Link>
        ) : (
          <Typography
            key={linkItem.name}
            color={linkItem.isActive ? "text.primary" : "inherit"}
          >
            {linkItem.name}
          </Typography>
        ),
      )}
    </Breadcrumbs>
  );
}
