import * as React from "react";
import { Box, Breadcrumbs, Link, Typography } from "@mui/material";
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
      {links.map((linkItem) => {
        if (linkItem.href) {
          return (
            <Link
              underline="hover"
              key={linkItem.href}
              component={NextLink}
              color="inherit"
              href={linkItem.href}
            >
              {linkItem.name}
            </Link>
          );
        }
        return (
          <Typography
            key={linkItem.name}
            color={linkItem.isActive ? "text.primary" : "inherit"}
          >
            {linkItem.name}
          </Typography>
        );
      })}
    </Breadcrumbs>
  );
}
