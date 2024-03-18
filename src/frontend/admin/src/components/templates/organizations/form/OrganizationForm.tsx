import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import { Organization } from "@/services/api/models/Organization";
import { OrganizationAddressForm } from "@/components/templates/organizations/form/sections/OrganizationAddressForm";
import { OrganizationGeneralSection } from "@/components/templates/organizations/form/sections/OrganizationGeneralSection";
import { OrganizationFormMemberSection } from "@/components/templates/organizations/form/sections/OrganizationMemberSection";
import {
  TabsComponent,
  TabValue,
} from "@/components/presentational/tabs/TabsComponent";

const messages = defineMessages({
  generalTabTitle: {
    id: "components.templates.organizations.address.form.translations.generalTabTitle",
    defaultMessage: "General",
    description: "Title for general tab",
  },
  addressTabTitle: {
    id: "components.templates.organizations.address.form.translations.addressTabTitle",
    defaultMessage: "Address",
    description: "Title for address tab",
  },
  memberTabTitle: {
    id: "components.templates.organizations.address.form.translations.memberTabTitle",
    defaultMessage: "Members",
    description: "Title for members tab",
  },
  generalTabInfo: {
    id: "components.templates.organizations.address.form.translations.generalTabInfo",
    defaultMessage:
      "In this section, you can provide general information, give information on the signatories or even on the legal part of the organization",
    description: "Text for general tab info",
  },
  addressTabInfo: {
    id: "components.templates.organizations.address.form.translations.addressTabInfo",
    defaultMessage:
      "In this section, you must fill in the details of the organization's address",
    description: "Text for address tab info",
  },
  memberTabInfo: {
    id: "components.templates.organizations.address.form.translations.memberTabInfo",
    defaultMessage:
      "In this section, you can manage the members of the organization and their roles. Please note, there must be at least one owner of the organization",
    description: "Text for members tab info",
  },
});

interface Props {
  afterSubmit?: (values: Organization) => void;
  organization?: Organization;
  fromOrganization?: Organization;
}

export function OrganizationForm(props: Props) {
  const intl = useIntl();
  const defaultOrganization = props.organization ?? props.fromOrganization;
  const tabs = useMemo(() => {
    let result: TabValue[] = [
      {
        label: intl.formatMessage(messages.generalTabTitle),
        tabInfo: intl.formatMessage(messages.generalTabInfo),
        component: (
          <OrganizationGeneralSection
            organization={defaultOrganization}
            afterSubmit={props.afterSubmit}
          />
        ),
      },
    ];

    if (props.organization) {
      result = [
        ...result,
        {
          label: intl.formatMessage(messages.addressTabTitle),
          tabInfo: intl.formatMessage(messages.addressTabInfo),
          show: !!defaultOrganization,
          component: (
            <OrganizationAddressForm organization={props.organization} />
          ),
        },
        {
          label: intl.formatMessage(messages.memberTabTitle),
          tabInfo: intl.formatMessage(messages.memberTabInfo),
          component: (
            <OrganizationFormMemberSection organization={props.organization} />
          ),
        },
      ];
    }
    return result;
  }, [props.organization, defaultOrganization, intl]);

  return <TabsComponent id="organization-form-tabs" tabs={tabs} />;
}
