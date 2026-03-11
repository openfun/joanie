import * as React from "react";
import Switch from "@mui/material/Switch";
import { defineMessages, useIntl } from "react-intl";
import { SxProps } from "@mui/material/styles";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import {
  OfferingDeepLink,
  OfferingDeepLinkDummy,
} from "@/services/api/models/OfferingDeepLink";
import { Organization } from "@/services/api/models/Organization";

const messages = defineMessages({
  isActiveSwitchAriaLabel: {
    id: "components.templates.courses.form.offering.deepLinkRow.isActiveSwitchAriaLabel",
    description: "Aria-label for the deep link is active switch",
    defaultMessage: "Deep link is active switch",
  },
  deleteDisabledMessage: {
    id: "components.templates.courses.form.offering.deepLinkRow.deleteDisabledMessage",
    description:
      "Message shown when delete is disabled because deep link is active",
    defaultMessage: "You cannot delete this offering deep link, it's active.",
  },
});

const isOfferingDeepLink = (
  item: OfferingDeepLink | OfferingDeepLinkDummy,
): item is OfferingDeepLink => {
  if (!item) return false;
  return "id" in item;
};

const isOfferingDeepLinkDummy = (
  item: OfferingDeepLink | OfferingDeepLinkDummy,
): item is OfferingDeepLinkDummy => {
  if (!item) return false;
  return "dummyId" in item;
};

type Props = {
  deepLink: OfferingDeepLink | OfferingDeepLinkDummy;
  organizations: Organization[];
  onDelete?: () => void;
  onEdit?: () => void;
  onUpdateIsActive?: (isActive: boolean) => void;
};

export function OfferingDeepLinkRow({
  deepLink,
  organizations,
  onDelete,
  onEdit,
  onUpdateIsActive,
}: Props) {
  const intl = useIntl();

  const getOrganizationTitle = (organizationId: string): string => {
    return (
      organizations.find((org) => org.id === organizationId)?.title ??
      organizationId
    );
  };

  const sxProps: SxProps = { backgroundColor: "background" };

  if (isOfferingDeepLinkDummy(deepLink)) {
    return (
      <DefaultRow
        testId={`offering-deep-link-${deepLink.dummyId}`}
        key={deepLink.dummyId}
        enableDelete={false}
        enableEdit={false}
        loading={true}
        sx={sxProps}
        mainTitle={getOrganizationTitle(deepLink.organization)}
        subTitle={deepLink.deep_link}
      />
    );
  }

  if (isOfferingDeepLink(deepLink)) {
    const canDelete = !deepLink.is_active;
    return (
      <DefaultRow
        testId={`offering-deep-link-${deepLink.id}`}
        key={deepLink.id}
        deleteTestId={`delete-offering-deep-link-${deepLink.id}`}
        enableDelete={canDelete}
        enableEdit={true}
        disableDeleteMessage={
          !canDelete
            ? intl.formatMessage(messages.deleteDisabledMessage)
            : undefined
        }
        onDelete={onDelete}
        onEdit={onEdit}
        sx={sxProps}
        mainTitle={getOrganizationTitle(deepLink.organization)}
        subTitle={deepLink.deep_link}
        permanentRightActions={
          <Switch
            inputProps={{
              "aria-label": intl.formatMessage(
                messages.isActiveSwitchAriaLabel,
              ),
            }}
            size="small"
            data-testid={`is-active-switch-offering-deep-link-${deepLink.id}`}
            onChange={(_, checked) => onUpdateIsActive?.(checked)}
            checked={deepLink.is_active}
          />
        }
      />
    );
  }

  return undefined;
}
