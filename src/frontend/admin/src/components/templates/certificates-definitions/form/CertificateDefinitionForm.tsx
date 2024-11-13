import * as React from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Grid2";
import { defineMessages, useIntl } from "react-intl";
import Box from "@mui/material/Box";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { useCertificateDefinitions } from "@/hooks/useCertificateDefinitions/useCertificateDefinitions";
import { ServerSideErrorForm } from "@/types/utils";
import { genericUpdateFormError } from "@/utils/forms";
import { TranslatableForm } from "@/components/presentational/translatable-content/TranslatableForm";
import {
  CertificateDefinition,
  CertificationDefinitionTemplate,
  DTOCertificateDefinition,
} from "@/services/api/models/CertificateDefinition";
import { RHFCertificateDefinitionTemplates } from "@/components/templates/certificates-definitions/inputs/RHFCertificateDefinitionTemplate";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { useFormSubmit } from "@/hooks/form/useFormSubmit";

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
  const formSubmitProps = useFormSubmit(definition);
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
      template: CertificationDefinitionTemplate.CERTIFICATE,
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
    const newValues: DTOCertificateDefinition = {
      ...values,
    };
    if (definition) {
      newValues.id = definition.id;
      certificateDefinitions.methods.update(newValues, {
        onError: (error) => updateFormError(error.data),
        onSuccess: (updatedCertificate) =>
          props.afterSubmit?.(updatedCertificate),
      });
    } else {
      certificateDefinitions.methods.create(newValues, {
        onError: (error) => updateFormError(error.data),
        onSuccess: (updatedCertificate) =>
          props.afterSubmit?.(updatedCertificate),
      });
    }
  };

  return (
    <TranslatableForm
      resetForm={() => methods.reset(getDefaultValues())}
      entitiesDeps={[definition]}
      onSelectLang={async () => {
        if (definition) {
          await certificateDefinitions.methods.invalidate();
        }
      }}
    >
      <Box padding={4}>
        <RHFProvider
          checkBeforeUnload={true}
          showSubmit={formSubmitProps.showSubmit}
          methods={methods}
          id="certificate-definition-form"
          onSubmit={methods.handleSubmit(onSubmit)}
        >
          <RHFValuesChange
            autoSave={formSubmitProps.enableAutoSave}
            onSubmit={onSubmit}
          >
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 6 }}>
                <RHFTextField
                  name="title"
                  label={intl.formatMessage(messages.titleLabel)}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <RHFTextField
                  name="name"
                  label={intl.formatMessage(messages.nameLabel)}
                />
              </Grid>
              <Grid size={12}>
                <RHFCertificateDefinitionTemplates name="template" />
              </Grid>
              <Grid size={12}>
                <RHFTextField
                  name="description"
                  multiline
                  minRows={5}
                  label={intl.formatMessage(messages.descriptionLabel)}
                />
              </Grid>
            </Grid>
          </RHFValuesChange>
        </RHFProvider>
      </Box>
    </TranslatableForm>
  );
}
