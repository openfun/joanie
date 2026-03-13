import * as React from "react";
import { useEffect } from "react";
import { defineMessages, useIntl } from "react-intl";
import * as Yup from "yup";
import { useForm, Controller } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid2 from "@mui/material/Grid2";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import RHFSwitch from "@/components/presentational/hook-form/RHFSwitch";
import { Maybe } from "@/types/utils";
import { OfferingDeepLink } from "@/services/api/models/OfferingDeepLink";
import { Organization } from "@/services/api/models/Organization";

const messages = defineMessages({
  organizationLabel: {
    id: "components.templates.courses.form.offering.deepLinkForm.organizationLabel",
    defaultMessage: "Organization",
    description: "The input label for the organization select",
  },
  deepLinkLabel: {
    id: "components.templates.courses.form.offering.deepLinkForm.deepLinkLabel",
    defaultMessage: "Deep link URL",
    description: "The input label for the deep link URL",
  },
  isActiveLabel: {
    id: "components.templates.courses.form.offering.deepLinkForm.isActiveLabel",
    defaultMessage: "Activate this deep link",
    description: "The input label for the activate switch",
  },
});

export type OfferingDeepLinkFormValues = {
  organization_id: string;
  deep_link: string;
  is_active: boolean;
};

type Props = {
  deepLink?: Maybe<OfferingDeepLink>;
  organizations: Organization[];
  onSubmit?: (values: OfferingDeepLinkFormValues) => void;
};

export function OfferingDeepLinkForm({
  deepLink,
  organizations,
  onSubmit,
}: Props) {
  const intl = useIntl();

  const Schema = Yup.object().shape({
    organization_id: Yup.string().required(),
    deep_link: Yup.string().url().max(200).required(),
    is_active: Yup.boolean().required(),
  });

  const getDefaultValues = (): OfferingDeepLinkFormValues => ({
    organization_id: deepLink?.organization ?? "",
    deep_link: deepLink?.deep_link ?? "",
    is_active: deepLink?.is_active ?? false,
  });

  const form = useForm({
    resolver: yupResolver(Schema),
    defaultValues: getDefaultValues(),
  });

  useEffect(() => {
    form.reset(getDefaultValues());
  }, [deepLink]);

  return (
    <RHFProvider
      methods={form}
      id="offering-deep-link-form"
      onSubmit={form.handleSubmit((values) => onSubmit?.(values))}
    >
      <Grid2 container spacing={2}>
        <Grid2 size={12}>
          <Controller
            name="organization_id"
            control={form.control}
            render={({ field, fieldState }) => (
              <TextField
                {...field}
                select={true}
                fullWidth={true}
                label={intl.formatMessage(messages.organizationLabel)}
                error={!!fieldState.error}
                helperText={fieldState.error?.message}
              >
                {organizations.map((org) => (
                  <MenuItem key={org.id} value={org.id}>
                    {org.title}
                  </MenuItem>
                ))}
              </TextField>
            )}
          />
        </Grid2>
        <Grid2 size={12}>
          <RHFTextField
            name="deep_link"
            label={intl.formatMessage(messages.deepLinkLabel)}
          />
        </Grid2>
        <Grid2 size={12}>
          <RHFSwitch
            name="is_active"
            label={intl.formatMessage(messages.isActiveLabel)}
          />
        </Grid2>
      </Grid2>
    </RHFProvider>
  );
}
