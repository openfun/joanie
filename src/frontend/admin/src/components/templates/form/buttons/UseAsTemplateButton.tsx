import * as React from "react";
import NextLink from "next/link";
import Button from "@mui/material/Button";
import { useIntl } from "react-intl";
import { commonTranslations } from "@/translations/common/commonTranslations";

type Props = {
  href: string;
  show: boolean | undefined;
};
export function UseAsTemplateButton({ href, show }: Props) {
  const intl = useIntl();

  if (!show) {
    return null;
  }

  return (
    <Button
      href={href}
      variant="outlined"
      color="secondary"
      LinkComponent={NextLink}
    >
      {intl.formatMessage(commonTranslations.useAsTemplate)}
    </Button>
  );
}
