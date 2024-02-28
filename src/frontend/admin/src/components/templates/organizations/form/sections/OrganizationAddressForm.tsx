import * as React from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Unstable_Grid2";
import { FormattedMessage, useIntl } from "react-intl";
import Typography from "@mui/material/Typography";
import {
  DTOOrganizationAddress,
  Organization,
} from "@/services/api/models/Organization";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { useOrganizations } from "@/hooks/useOrganizations/useOrganizations";
import { organizationAddressFormMessages } from "@/components/templates/organizations/form/translations";
import { RHFSelect } from "@/components/presentational/hook-form/RHFSelect";

type Props = {
  organization: Organization;
};
export function OrganizationAddressForm({ organization }: Props) {
  const intl = useIntl();
  const organizationQuery = useOrganizations({}, { enabled: false });
  const organizationAddress = organization?.addresses?.find(
    (address) => address.is_main,
  );

  const getDefaultValues = () => {
    return {
      title: organizationAddress?.title ?? "",
      country: organizationAddress?.country ?? "FR",
      address: organizationAddress?.address ?? "",
      postcode: organizationAddress?.postcode ?? "",
      city: organizationAddress?.city ?? "",
      first_name: organizationAddress?.first_name ?? "",
      last_name: organizationAddress?.last_name ?? "",
    };
  };

  const RegisterSchema = Yup.object().shape({
    title: Yup.string().required(),
    address: Yup.string().required(),
    postcode: Yup.string().required(),
    city: Yup.string().required(),
    country: Yup.string().required(),
    first_name: Yup.string().required(),
    last_name: Yup.string().required(),
  });

  const methods = useForm({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues() as any, // To not trigger type validation for default value
  });

  const onSubmit = async (payload: DTOOrganizationAddress) => {
    payload.is_main = true;
    payload.is_reusable = true;
    if (!organizationAddress) {
      await organizationQuery.methods.addAddress(organization.id, payload);
    } else {
      await organizationQuery.methods.updateAddress(
        organization.id,
        organizationAddress.id,
        payload,
      );
    }
  };

  return (
    <SimpleCard>
      <Box padding={4}>
        <RHFProvider
          methods={methods}
          checkBeforeUnload={true}
          id="organization-address-form"
          onSubmit={methods.handleSubmit(onSubmit)}
        >
          <Grid container spacing={2}>
            <Grid xs={12}>
              <Typography variant="subtitle2">
                <FormattedMessage
                  {...organizationAddressFormMessages.sectionTitle}
                />
              </Typography>
            </Grid>
            <Grid xs={12}>
              <RHFTextField
                name="title"
                label={intl.formatMessage(
                  organizationAddressFormMessages.titleLabel,
                )}
              />
            </Grid>
            <Grid xs={12}>
              <RHFTextField
                name="address"
                label={intl.formatMessage(
                  organizationAddressFormMessages.addressLabel,
                )}
              />
            </Grid>
            <Grid xs={12} sm={6}>
              <RHFTextField
                name="postcode"
                label={intl.formatMessage(
                  organizationAddressFormMessages.postCodeLabel,
                )}
              />
            </Grid>
            <Grid xs={12} sm={6}>
              <RHFTextField
                name="city"
                label={intl.formatMessage(
                  organizationAddressFormMessages.cityLabel,
                )}
              />
            </Grid>
            <Grid xs={12}>
              <RHFSelect
                disabled={!organizationQuery.countries}
                name="country"
                options={organizationQuery.countries ?? []}
                label={intl.formatMessage(
                  organizationAddressFormMessages.countryLabel,
                )}
              />
            </Grid>
            <Grid xs={12} sm={6}>
              <RHFTextField
                name="first_name"
                label={intl.formatMessage(
                  organizationAddressFormMessages.firstNameLabel,
                )}
              />
            </Grid>
            <Grid xs={12} sm={6}>
              <RHFTextField
                name="last_name"
                label={intl.formatMessage(
                  organizationAddressFormMessages.lastNameLabel,
                )}
              />
            </Grid>
          </Grid>
        </RHFProvider>
      </Box>
    </SimpleCard>
  );
}
