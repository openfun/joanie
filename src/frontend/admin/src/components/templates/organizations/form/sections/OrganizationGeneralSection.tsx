import * as React from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Unstable_Grid2";
import { FormattedMessage, useIntl } from "react-intl";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { RHFUploadImage } from "@/components/presentational/hook-form/RHFUploadImage";
import {
  DTOOrganization,
  Organization,
} from "@/services/api/models/Organization";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { organizationFormMessages } from "@/components/templates/organizations/form/translations";
import { useOrganizations } from "@/hooks/useOrganizations/useOrganizations";
import { Maybe, ServerSideErrorForm } from "@/types/utils";
import { genericUpdateFormError } from "@/utils/forms";
import { TranslatableForm } from "@/components/presentational/translatable-content/TranslatableForm";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { ThumbnailDetailField } from "@/services/api/models/Image";
import { RHFSelect } from "@/components/presentational/hook-form/RHFSelect";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { useFormSubmit } from "@/hooks/form/useFormSubmit";

interface FormValues {
  code: string;
  title: string;
  representative: string | undefined;
  signature: File[] | undefined;
  logo: File[] | undefined;
  enterprise_code?: string; // SIRET in France
  activity_category_code?: string; // APE in France
  representative_profession?: string;
  signatory_representative?: string;
  signatory_representative_profession?: string;
  contact_phone?: string;
  contact_email?: string;
  dpo_email?: string;
}

interface Props {
  afterSubmit?: (values: Organization) => void;
  organization?: Organization;
  fromOrganization?: Organization;
}

export function OrganizationGeneralSection(props: Props) {
  const intl = useIntl();
  const formSubmitProps = useFormSubmit(props.organization);
  const organizationQuery = useOrganizations({}, { enabled: false });
  const defaultOrganization = props.organization ?? props.fromOrganization;

  const getDefaultValues = () => {
    return {
      code: defaultOrganization?.code ?? "",
      title: defaultOrganization?.title ?? "",
      representative: defaultOrganization?.representative ?? "",
      country: defaultOrganization?.country ?? "FR",
      enterprise_code: defaultOrganization?.enterprise_code ?? "",
      activity_category_code: defaultOrganization?.activity_category_code ?? "",
      representative_profession:
        defaultOrganization?.representative_profession ?? "",
      signatory_representative:
        defaultOrganization?.signatory_representative ?? "",
      signatory_representative_profession:
        defaultOrganization?.signatory_representative_profession ?? "",
      contact_phone: defaultOrganization?.contact_phone ?? "",
      contact_email: defaultOrganization?.contact_email ?? "",
      dpo_email: defaultOrganization?.dpo_email ?? "",
    };
  };

  const RegisterSchema = Yup.object().shape({
    code: Yup.string().required(),
    title: Yup.string().required(),
    representative: Yup.string(),
    signature: Yup.mixed(),
    logo: Yup.mixed(),
    country: Yup.string(),
    enterprise_code: Yup.string(),
    activity_category_code: Yup.string(),
    representative_profession: Yup.string(),
    signatory_representative: Yup.string(),
    signatory_representative_profession: Yup.string().when(
      ["signatory_representative"],
      {
        is: (signatory_representative: Maybe<string>) =>
          signatory_representative != null && signatory_representative !== "",
        then: (schema) => schema.required(),
      },
    ),
    contact_phone: Yup.string(),
    contact_email: Yup.string().email(),
    dpo_email: Yup.string().email(),
  });

  const methods = useForm({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues() as any, // To not trigger type validation for default value
  });

  const updateFormError = (errors: ServerSideErrorForm<FormValues>) => {
    genericUpdateFormError(errors, methods.setError);
  };

  const onSubmit = (values: FormValues): void => {
    const payload: DTOOrganization = {
      ...values,
      logo: values.logo?.[0],
      signature: values.signature?.[0],
    };

    if (values.logo?.[0] === undefined) {
      delete payload.logo;
    }
    if (values.signature?.[0] === undefined) {
      delete payload.signature;
    }

    if (props.organization) {
      payload.id = props.organization.id;
      organizationQuery.methods.update(payload, {
        onSuccess: (data) => props.afterSubmit?.(data),
        onError: (error) => updateFormError(error.data),
      });
    } else {
      organizationQuery.methods.create(payload, {
        onSuccess: (data) => props.afterSubmit?.(data),
        onError: (error) => updateFormError(error.data),
      });
    }
  };

  const getUploadedSignature = (): ThumbnailDetailField[] => {
    if (!organizationQuery) {
      return [];
    }
    return defaultOrganization?.signature
      ? [defaultOrganization.signature]
      : [];
  };

  const getUploadedLogo = (): ThumbnailDetailField[] => {
    if (!organizationQuery) {
      return [];
    }
    return defaultOrganization?.logo ? [defaultOrganization.logo] : [];
  };

  const { handleSubmit } = methods;
  return (
    <SimpleCard>
      <TranslatableForm
        entitiesDeps={[props.organization]}
        resetForm={() => methods.reset(getDefaultValues())}
        onSelectLang={() => {
          if (props.organization) organizationQuery.methods.invalidate();
        }}
      >
        <Box padding={4}>
          <RHFProvider
            checkBeforeUnload={true}
            showSubmit={formSubmitProps.showSubmit}
            methods={methods}
            isSubmitting={organizationQuery.states.updating}
            id="organization-form"
            onSubmit={handleSubmit(onSubmit)}
          >
            <RHFValuesChange
              autoSave={formSubmitProps.enableAutoSave}
              onSubmit={onSubmit}
            >
              <Grid container spacing={2}>
                <Grid xs={12}>
                  <Typography variant="subtitle2">
                    <FormattedMessage
                      {...organizationFormMessages.generalSectionTitle}
                    />
                  </Typography>
                </Grid>

                <Grid xs={12} md={6}>
                  <RHFTextField
                    name="title"
                    label={intl.formatMessage(commonTranslations.title)}
                  />
                </Grid>
                <Grid xs={12} md={6}>
                  <RHFTextField
                    name="code"
                    label={intl.formatMessage(
                      organizationFormMessages.codeLabel,
                    )}
                  />
                </Grid>

                <Grid xs={12} md={6}>
                  <RHFTextField
                    name="representative"
                    label={intl.formatMessage(
                      organizationFormMessages.representativeLabel,
                    )}
                  />
                </Grid>
                <Grid xs={12} md={6}>
                  <RHFTextField
                    name="representative_profession"
                    label={intl.formatMessage(
                      organizationFormMessages.representativeProfessionLabel,
                    )}
                  />
                </Grid>

                <Grid xs={12}>
                  <RHFSelect
                    disabled={!organizationQuery.countries}
                    name="country"
                    options={organizationQuery.countries ?? []}
                    label={intl.formatMessage(
                      organizationFormMessages.countryLabel,
                    )}
                  />
                </Grid>

                <Grid xs={12}>
                  <RHFUploadImage
                    thumbnailFiles={getUploadedLogo()}
                    buttonLabel={intl.formatMessage(
                      organizationFormMessages.uploadLogoButtonLabel,
                    )}
                    name="logo"
                    accept="image/*"
                    label={intl.formatMessage(
                      organizationFormMessages.logoLabel,
                    )}
                  />
                </Grid>

                <Grid xs={12}>
                  <Typography variant="subtitle2">
                    <FormattedMessage
                      {...organizationFormMessages.signatoryDetailsSectionTitle}
                    />
                  </Typography>
                </Grid>

                <Grid xs={12}>
                  <Alert severity="info">
                    <FormattedMessage
                      {...organizationFormMessages.signatoryDetailsSectionInfo}
                    />
                  </Alert>
                </Grid>

                <Grid xs={12} md={6}>
                  <RHFTextField
                    name="signatory_representative"
                    label={intl.formatMessage(
                      organizationFormMessages.signatoryRepresentativeLabel,
                    )}
                  />
                </Grid>

                <Grid xs={12} md={6}>
                  <RHFTextField
                    name="signatory_representative_profession"
                    helperText={intl.formatMessage(
                      organizationFormMessages.signatoryRepresentativeProfessionHelperText,
                    )}
                    label={intl.formatMessage(
                      organizationFormMessages.signatoryRepresentativeProfessionLabel,
                    )}
                  />
                </Grid>
                <Grid xs={12}>
                  <RHFUploadImage
                    thumbnailFiles={getUploadedSignature()}
                    name="signature"
                    buttonLabel={intl.formatMessage(
                      organizationFormMessages.uploadSignatureButtonLabel,
                    )}
                    accept="image/*"
                    label={intl.formatMessage(
                      organizationFormMessages.signatureLabel,
                    )}
                  />
                </Grid>

                <Grid xs={12}>
                  <Typography variant="subtitle2">
                    <FormattedMessage
                      {...organizationFormMessages.legalPartSectionTitle}
                    />
                  </Typography>
                </Grid>
                <Grid xs={12} md={6}>
                  <RHFTextField
                    name="enterprise_code"
                    label={intl.formatMessage(
                      organizationFormMessages.enterpriseCodeLabel,
                    )}
                  />
                </Grid>
                <Grid xs={12} lg={6}>
                  <RHFTextField
                    name="activity_category_code"
                    label={intl.formatMessage(
                      organizationFormMessages.activityCategoryCodeLabel,
                    )}
                  />
                </Grid>

                <Grid xs={12}>
                  <Typography variant="subtitle2">
                    <FormattedMessage
                      {...organizationFormMessages.contactSectionTitle}
                    />
                  </Typography>
                </Grid>
                <Grid xs={12} md={6} lg={4}>
                  <RHFTextField
                    name="contact_phone"
                    label={intl.formatMessage(
                      organizationFormMessages.contactPhoneLabel,
                    )}
                  />
                </Grid>
                <Grid xs={12} md={6} lg={4}>
                  <RHFTextField
                    name="contact_email"
                    label={intl.formatMessage(
                      organizationFormMessages.contactEmailLabel,
                    )}
                  />
                </Grid>
                <Grid xs={12} lg={4}>
                  <RHFTextField
                    name="dpo_email"
                    label={intl.formatMessage(
                      organizationFormMessages.dpoContactEmailLabel,
                    )}
                  />
                </Grid>
              </Grid>
            </RHFValuesChange>
          </RHFProvider>
        </Box>
      </TranslatableForm>
    </SimpleCard>
  );
}
