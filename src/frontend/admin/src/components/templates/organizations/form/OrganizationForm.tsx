import * as React from "react";
import { useEffect } from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Unstable_Grid2";
import { useIntl } from "react-intl";
import Box from "@mui/material/Box";
import LoadingButton from "@mui/lab/LoadingButton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { RHFUpload } from "@/components/presentational/hook-form/RHFUpload";
import {
  DTOOrganization,
  Organization,
  OrganizationRoles,
} from "@/services/api/models/Organization";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { organizationFormMessages } from "@/components/templates/organizations/form/translations";
import { useOrganizations } from "@/hooks/useOrganizations/useOrganizations";
import { ServerSideErrorForm } from "@/types/utils";
import { genericUpdateFormError } from "@/utils/forms";
import { TranslatableContent } from "@/components/presentational/translatable-content/TranslatableContent";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { AccessesList } from "@/components/templates/accesses/list/AccessesList";
import { LoadingContent } from "@/components/presentational/loading/LoadingContent";

interface FormValues {
  code: string;
  title: string;
  representative: string | undefined;
  signature: File[] | undefined;
  logo: File[] | undefined;
}

interface Props {
  afterSubmit?: (values: Organization) => void;
  organization?: Organization;
}

export function OrganizationForm(props: Props) {
  const intl = useIntl();
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
    <Stack spacing={3}>
      <SimpleCard>
        <TranslatableContent
          onSelectLang={() => {
            if (props.organization) org.methods.invalidate();
          }}
        >
          <Box padding={4}>
            <RHFProvider
              showSubmit={false}
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
                  <RHFUpload
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
                <Grid xs={12} md={6}>
                  <RHFUpload
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
              </Grid>
            </RHFProvider>

            <Box display="flex" mt={2} alignItems="center" justifyContent="end">
              <LoadingButton
                loading={org.states.updating}
                onClick={handleSubmit(onSubmit)}
                variant="contained"
              >
                {intl.formatMessage(commonTranslations.submit)}
              </LoadingButton>
            </Box>
          </Box>
        </TranslatableContent>
      </SimpleCard>
      <LoadingContent loading={org.accesses === undefined}>
        {props.organization && org.accesses && (
          <SimpleCard>
            <Box padding={4}>
              <Typography>
                {intl.formatMessage(
                  organizationFormMessages.membersSectionTitle,
                )}
              </Typography>
            </Box>
            <AccessesList
              defaultRole={OrganizationRoles.MEMBER}
              onRemove={async (accessId) => {
                await org.methods.removeAccessUser(
                  // @ts-ignore
                  props.organization?.id,
                  accessId,
                );
              }}
              onUpdateAccess={(accessId, payload) => {
                return org.methods.updateAccessUser(
                  // @ts-ignore
                  props.organization.id,
                  accessId,
                  payload,
                );
              }}
              onAdd={(user, role) => {
                if (props.organization?.id && user.id) {
                  org.methods.addAccessUser(
                    props.organization?.id,
                    user.id,
                    role,
                  );
                }
              }}
              accesses={props.organization?.accesses ?? []}
              availableAccesses={org.accesses}
            />
          </SimpleCard>
        )}
      </LoadingContent>
    </Stack>
  );
}
