import * as React from "react";
import { useEffect } from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Unstable_Grid2";
import { useIntl } from "react-intl";
import { useSnackbar } from "notistack";
import Box from "@mui/material/Box";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { RHFUpload } from "@/components/presentational/hook-form/RHFUpload";
import {
  DTOOrganization,
  Organization,
} from "@/services/api/models/Organization";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { organizationFormMessages } from "@/components/templates/organizations/form/translations";
import { useOrganizations } from "@/hooks/useOrganizations/useOrganizations";
import { ServerSideErrorForm } from "@/types/utils";
import { genericUpdateFormError } from "@/utils/forms";
import { TranslatableContent } from "@/components/presentational/translatable-content/TranslatableContent";

interface FormValues {
  code: string;
  title: string;
  representative?: string;
  signature?: File[];
  logo?: File[];
}

interface Props {
  afterSubmit?: (values: Organization) => void;
  organization?: Organization;
}

export function OrganizationForm(props: Props) {
  const intl = useIntl();
  const snackbar = useSnackbar();
  const org = useOrganizations({}, { enabled: false });

  const getDefaultValues = () => {
    return {
      code: props.organization?.code ?? "",
      title: props.organization?.title ?? "",
      representative: props.organization?.representative ?? "",
    };
  };

  const RegisterSchema = Yup.object().shape({
    code: Yup.string().required(),
    title: Yup.string().required(),
    representative: Yup.string(),
    signature: Yup.mixed(),
    logo: Yup.mixed(),
  });

  const methods = useForm<FormValues>({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues(),
  });

  const updateFormError = (errors: ServerSideErrorForm<FormValues>) => {
    genericUpdateFormError(errors, methods.setError);
  };

  useEffect(() => {
    if (org.states.error) {
      snackbar.enqueueSnackbar(org.states.error, { variant: "error" });
    }
  }, [org.states.error]);

  const onSubmit = (values: FormValues): void => {
    const payload: DTOOrganization = {
      ...values,
      logo: values.logo?.[0],
      signature: values.signature?.[0],
    };

    if (props.organization) {
      payload.id = props.organization.id;
      org.methods.update(payload, {
        onSuccess: (data) => props.afterSubmit?.(data),
        onError: (error) => updateFormError(error.data),
      });
    } else {
      org.methods.create(payload, {
        onSuccess: (data) => props.afterSubmit?.(data),
        onError: (error) => updateFormError(error.data),
      });
    }
  };

  useEffect(() => {
    methods.reset(getDefaultValues());
  }, [props.organization]);

  const { handleSubmit } = methods;
  return (
    <TranslatableContent
      onSelectLang={() => {
        if (props.organization) org.methods.invalidate();
      }}
    >
      <Box padding={4}>
        <RHFProvider
          methods={methods}
          isSubmitting={org.states.updating}
          id="organization-form"
          onSubmit={handleSubmit(onSubmit)}
        >
          <Grid container spacing={2}>
            <Grid xs={12}>
              <RHFTextField
                name="title"
                label={intl.formatMessage(commonTranslations.title)}
              />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFTextField
                name="code"
                label={intl.formatMessage(organizationFormMessages.codeLabel)}
              />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFTextField
                name="representative"
                label={intl.formatMessage(
                  organizationFormMessages.representativeLabel
                )}
              />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFUpload
                buttonLabel={intl.formatMessage(
                  organizationFormMessages.uploadLogoButtonLabel
                )}
                name="logo"
                accept="image/*"
                label={intl.formatMessage(organizationFormMessages.logoLabel)}
              />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFUpload
                name="signature"
                buttonLabel={intl.formatMessage(
                  organizationFormMessages.uploadSignatureButtonLabel
                )}
                accept="image/*"
                label={intl.formatMessage(
                  organizationFormMessages.signatureLabel
                )}
              />
            </Grid>
          </Grid>
        </RHFProvider>
      </Box>
    </TranslatableContent>
  );
}
