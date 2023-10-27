import * as React from "react";
import { useEffect } from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Unstable_Grid2";
import { defineMessages, useIntl } from "react-intl";
import Box from "@mui/material/Box";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { RHFSelect } from "@/components/presentational/hook-form/RHFSelect";
import { useCertificateDefinitions } from "@/hooks/useCertificateDefinitions/useCertificateDefinitions";
import { ServerSideErrorForm } from "@/types/utils";
import { genericUpdateFormError } from "@/utils/forms";
import { TranslatableContent } from "@/components/presentational/translatable-content/TranslatableContent";
import {
  CertificateDefinition,
  DTOCertificateDefinition,
} from "@/services/api/models/CertificateDefinition";

const messages = defineMessages({
  titleLabel: {
    id: "components.templates.certificateDefinitions.form.titleLabel",
    defaultMessage: "Title",
    description: "Label for the title input",
  },
  nameLabel: {
    id: "components.templates.certificateDefinitions.form.nameLabel",
    defaultMessage: "Name",
    description: "Label for the name input",
  },
  templateLabel: {
    id: "components.templates.certificateDefinitions.form.templateLabel",
    defaultMessage: "Template",
    description: "Label for the template input",
  },
  descriptionLabel: {
    id: "components.templates.certificateDefinitions.form.descriptionLabel",
    defaultMessage: "Description",
    description: "Label for the name input",
  },
});

interface Props {
  afterSubmit?: (certificateDefinition: CertificateDefinition) => void;
  definition?: CertificateDefinition;
  fromDefinition?: CertificateDefinition;
}

export function CertificateDefinitionForm({ definition, ...props }: Props) {
  const intl = useIntl();
  const defaultDefinition = definition ?? props.fromDefinition;

  const certificateDefinitions = useCertificateDefinitions(
    {},
    { enabled: false },
  );
  const RegisterSchema = Yup.object().shape({
    name: Yup.string().required(),
    title: Yup.string().required(),
    description: Yup.string(),
    template: Yup.string(),
  });

  const getDefaultValues = () => {
    return {
      name: defaultDefinition?.name ?? "",
      title: defaultDefinition?.title ?? "",
      description: defaultDefinition?.description ?? "",
      template: "howard.issuers.CertificateDocument",
    };
  };

  const methods = useForm({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues(),
  });

  const updateFormError = (
    errors: ServerSideErrorForm<DTOCertificateDefinition>,
  ) => {
    genericUpdateFormError(errors, methods.setError);
  };

  const onSubmit = (values: DTOCertificateDefinition) => {
    if (definition) {
      values.id = definition.id;
      certificateDefinitions.methods.update(values, {
        onError: (error) => updateFormError(error.data),
        onSuccess: (updatedCertificate) =>
          props.afterSubmit?.(updatedCertificate),
      });
    } else {
      certificateDefinitions.methods.create(values, {
        onError: (error) => updateFormError(error.data),
        onSuccess: (updatedCertificate) =>
          props.afterSubmit?.(updatedCertificate),
      });
    }
  };

  useEffect(() => {
    methods.reset(getDefaultValues());
  }, [definition]);

  return (
    <TranslatableContent
      onSelectLang={() => {
        if (definition) certificateDefinitions.methods.invalidate();
      }}
    >
      <Box padding={4}>
        <RHFProvider
          methods={methods}
          id="certificate-definition-form"
          onSubmit={methods.handleSubmit(onSubmit)}
        >
          <Grid container spacing={2}>
            <Grid xs={12} md={6}>
              <RHFTextField
                name="title"
                label={intl.formatMessage(messages.titleLabel)}
              />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFTextField
                name="name"
                label={intl.formatMessage(messages.nameLabel)}
              />
            </Grid>
            <Grid xs={12}>
              <RHFSelect
                data-testid="template-select"
                name="template"
                disabled={true}
                options={[
                  {
                    label: "Default",
                    value: "howard.issuers.CertificateDocument",
                  },
                ]}
                label={intl.formatMessage(messages.templateLabel)}
              />
            </Grid>
            <Grid xs={12}>
              <RHFTextField
                name="description"
                multiline
                minRows={5}
                label={intl.formatMessage(messages.descriptionLabel)}
              />
            </Grid>
          </Grid>
        </RHFProvider>
      </Box>
    </TranslatableContent>
  );
}
