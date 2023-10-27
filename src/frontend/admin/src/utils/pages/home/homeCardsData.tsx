import { IntlShape } from "react-intl";
import AddShoppingCartIcon from "@mui/icons-material/AddShoppingCart";
import SchoolRoundedIcon from "@mui/icons-material/SchoolRounded";
import CalendarMonthIcon from "@mui/icons-material/CalendarMonth";
import CorporateFareRoundedIcon from "@mui/icons-material/CorporateFareRounded";
import TaskRoundedIcon from "@mui/icons-material/TaskRounded";
import * as React from "react";
import { PATH_ADMIN } from "@/utils/routes/path";
import { cardHomePagesTranslation } from "@/translations/pages/home/cardTranslations";

export const getHomeCardData = (intl: IntlShape) => [
  {
    title: intl.formatMessage(cardHomePagesTranslation.productTitle),
    description: intl.formatMessage(
      cardHomePagesTranslation.productDescription,
    ),
    badgeLabel: intl.formatMessage(cardHomePagesTranslation.productBadge),
    href: PATH_ADMIN.products.create,
    icon: <AddShoppingCartIcon />,
  },
  {
    title: intl.formatMessage(cardHomePagesTranslation.courseTitle),
    description: intl.formatMessage(cardHomePagesTranslation.courseDescription),
    badgeLabel: intl.formatMessage(cardHomePagesTranslation.courseBadge),
    href: PATH_ADMIN.courses.create,
    icon: <SchoolRoundedIcon />,
  },
  {
    title: intl.formatMessage(cardHomePagesTranslation.courseRunTitle),
    description: intl.formatMessage(
      cardHomePagesTranslation.courseRunDescription,
    ),
    badgeLabel: intl.formatMessage(cardHomePagesTranslation.courseRunBadge),
    href: PATH_ADMIN.courses_run.create,
    icon: <CalendarMonthIcon />,
  },
  {
    title: intl.formatMessage(cardHomePagesTranslation.organizationTitle),
    description: intl.formatMessage(
      cardHomePagesTranslation.organizationDescription,
    ),
    badgeLabel: intl.formatMessage(cardHomePagesTranslation.organizationBadge),
    href: PATH_ADMIN.organizations.create,
    icon: <CorporateFareRoundedIcon />,
  },
  {
    title: intl.formatMessage(
      cardHomePagesTranslation.certificateDefinitionTitle,
    ),
    description: intl.formatMessage(
      cardHomePagesTranslation.certificateDefinitionDescription,
    ),
    badgeLabel: intl.formatMessage(
      cardHomePagesTranslation.certificateDefinitionBadge,
    ),
    href: PATH_ADMIN.certificates.create,
    icon: <TaskRoundedIcon />,
  },
];
