import { defineMessages } from "react-intl";
import React, { ReactElement } from "react";
import CorporateFareRoundedIcon from "@mui/icons-material/CorporateFareRounded";
import SchoolRoundedIcon from "@mui/icons-material/SchoolRounded";
import EventAvailableRoundedIcon from "@mui/icons-material/EventAvailableRounded";
import TaskRoundedIcon from "@mui/icons-material/TaskRounded";
import ProductionQuantityLimitsRoundedIcon from "@mui/icons-material/ProductionQuantityLimitsRounded";
import { PATH_ADMIN } from "@/utils/routes/path";

const navTranslations = defineMessages({
  managementSubHeader: {
    id: "layouts.dashboard.nav.config.managementSubHeader",
    defaultMessage: "Management",
    description: "Subheader for the nav management section",
  },
  organizationNavTitle: {
    id: "layouts.dashboard.nav.config.organizationNavTitle",
    defaultMessage: "Organizations",
    description: "Title for the Organization nav item",
  },
  certificatesNavTitle: {
    id: "layouts.dashboard.nav.config.certificatesNavTitle",
    defaultMessage: "Certificates",
    description: "Title for the Certificates nav item",
  },
  courseNavTitle: {
    id: "layouts.dashboard.nav.config.courseNavTitle",
    defaultMessage: "Courses",
    description: "Title for the Courses nav item",
  },
  courseRunsNavTitle: {
    id: "layouts.dashboard.nav.config.courseRunsNavTitle",
    defaultMessage: "Courses runs",
    description: "Title for the Courses runs nav item",
  },
  productNavTitle: {
    id: "layouts.dashboard.nav.config.productNavTitle",
    defaultMessage: "Products",
    description: "Title for the Product nav item",
  },
});

export interface NavConfigItem {
  title: any;
  path: string;
  prefix: string;
  icon: ReactElement;
}
interface NavConfig {
  subheader?: any;
  items: NavConfigItem[];
}
export const navConfig: NavConfig[] = [
  {
    subheader: navTranslations.managementSubHeader,
    items: [
      {
        title: navTranslations.certificatesNavTitle,
        path: PATH_ADMIN.certificates.list,
        prefix: PATH_ADMIN.certificates.root,
        icon: <TaskRoundedIcon />,
      },
      {
        title: navTranslations.courseNavTitle,
        path: PATH_ADMIN.courses.list,
        prefix: PATH_ADMIN.courses.root,
        icon: <SchoolRoundedIcon />,
      },
      {
        title: navTranslations.courseRunsNavTitle,
        path: PATH_ADMIN.courses_run.list,
        prefix: PATH_ADMIN.courses_run.root,
        icon: <EventAvailableRoundedIcon />,
      },
      {
        title: navTranslations.organizationNavTitle,
        path: PATH_ADMIN.organizations.list,
        prefix: PATH_ADMIN.organizations.root,
        icon: <CorporateFareRoundedIcon />,
      },
      {
        title: navTranslations.productNavTitle,
        path: PATH_ADMIN.products.list,
        prefix: PATH_ADMIN.products.root,
        icon: <ProductionQuantityLimitsRoundedIcon />,
      },
    ],
  },
];
