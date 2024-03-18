import * as React from "react";
import { useIntl } from "react-intl";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import {
  Organization,
  OrganizationRoles,
} from "@/services/api/models/Organization";
import { organizationFormMessages } from "@/components/templates/organizations/form/translations";
import { useOrganizations } from "@/hooks/useOrganizations/useOrganizations";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { AccessesList } from "@/components/templates/accesses/list/AccessesList";
import { LoadingContent } from "@/components/presentational/loading/LoadingContent";

interface Props {
  organization?: Organization;
}

export function OrganizationFormMemberSection(props: Props) {
  const intl = useIntl();
  const organizationQuery = useOrganizations({}, { enabled: false });

  return (
    <LoadingContent loading={organizationQuery.accesses === undefined}>
      {props.organization && organizationQuery.accesses && (
        <SimpleCard>
          <Box padding={4}>
            <Typography>
              {intl.formatMessage(organizationFormMessages.membersSectionTitle)}
            </Typography>
          </Box>
          <AccessesList
            defaultRole={OrganizationRoles.MEMBER}
            onRemove={async (accessId) => {
              await organizationQuery.methods.removeAccessUser(
                // @ts-ignore
                props.organization?.id,
                accessId,
              );
            }}
            onUpdateAccess={(accessId, payload) => {
              return organizationQuery.methods.updateAccessUser(
                // @ts-ignore
                props.organization.id,
                accessId,
                payload,
              );
            }}
            onAdd={(user, role) => {
              if (props.organization?.id && user.id) {
                organizationQuery.methods.addAccessUser(
                  props.organization?.id,
                  user.id,
                  role,
                );
              }
            }}
            accesses={props.organization?.accesses ?? []}
            availableAccesses={organizationQuery.accesses}
          />
        </SimpleCard>
      )}
    </LoadingContent>
  );
}
