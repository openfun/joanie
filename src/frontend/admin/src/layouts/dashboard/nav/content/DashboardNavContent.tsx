import * as React from "react";
import Box from "@mui/material/Box";
import { useIntl } from "react-intl";
import { useRouter } from "next/router";
import { navConfig } from "@/layouts/dashboard/nav/config";
import { DashboardLayoutNavAccount } from "@/layouts/dashboard/nav/account/DashboardLayoutNavAccount";
import { DashboardNavItem } from "@/layouts/dashboard/nav/item/DashboardNavItem";
import { DashboardNavItemsList } from "@/layouts/dashboard/nav/item/list/DasboardNavItemsList";

interface Props {
  onChangeRoute?: (path?: string) => void;
}

export function DashboardNavContent(props: Props) {
  const intl = useIntl();
  const router = useRouter();

  const handleChangeRoute = (path: string): void => {
    router.push(path);
    props.onChangeRoute?.(path);
  };

  return (
    <Box sx={{ px: 2 }}>
      <DashboardLayoutNavAccount />
      {navConfig.map((config) => {
        const subheader = intl.formatMessage(config.subheader);
        return (
          <DashboardNavItemsList key={subheader} subHeaderTitle={subheader}>
            {config.items.map((item) => {
              const title = intl.formatMessage(item.title);
              const prefix = item.prefix + "/";
              return (
                <DashboardNavItem
                  key={`nav-item-${title}`}
                  icon={item.icon}
                  title={title}
                  isActive={router.pathname.startsWith(prefix)}
                  onClick={() => handleChangeRoute(item.path)}
                />
              );
            })}
          </DashboardNavItemsList>
        );
      })}
    </Box>
  );
}
