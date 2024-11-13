import * as React from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Grid2";
import { defineMessages, useIntl } from "react-intl";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import { ErrorMessage } from "@hookform/error-message";
import FormHelperText from "@mui/material/FormHelperText";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { ServerSideErrorForm } from "@/types/utils";
import { genericUpdateFormError } from "@/utils/forms";
import { useContractDefinitions } from "@/hooks/useContractDefinitions/useContractDefinitions";
import {
  ContractDefinition,
  DTOContractDefinition,
} from "@/services/api/models/ContractDefinition";
import { MarkdownComponent } from "@/components/presentational/inputs/markdown/MardownComponent";
import { removeEOL } from "@/utils/string";
import { RHFContractDefinitionLanguage } from "@/components/templates/contract-definition/inputs/RHFContractDefinitionLanguage";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { useFormSubmit } from "@/hooks/form/useFormSubmit";

const messages = defineMessages({
  informationText: {
    id: "components.templates.contractDefinitions.form.informationText",
    defaultMessage:
      "This is a contract template that will be used to issue contracts.",
    description: "Title for the information alert",
  },
  mainInformationTitle: {
    id: "components.templates.contractDefinitions.form.mainInformationTitle",
    defaultMessage: "Main information's",
    description: "Title for the main information section",
  },
  titleLabel: {
    id: "components.templates.contractDefinitions.form.titleLabel",
    defaultMessage: "Title",
    description: "Label for the title input",
  },
  languageLabel: {
    id: "components.templates.contractDefinitions.form.languageLabel",
    defaultMessage: "Language",
    description: "Label for the language input",
  },
  descriptionLabel: {
    id: "components.templates.contractDefinitions.form.descriptionLabel",
    defaultMessage: "Description",
    description: "Label for the name input",
  },
  bodyLabel: {
    id: "components.templates.contractDefinitions.form.bodyLabel",
    defaultMessage: "Body",
    description: "Label for the body input",
  },
  appendixLabel: {
    id: "components.templates.contractDefinitions.form.appendixLabel",
    defaultMessage: "Appendix",
    description: "Label for the appendix input",
  },
});

interface Props {
  afterSubmit?: (contractDefinition: ContractDefinition) => void;
  contractDefinition?: ContractDefinition;
  fromContractDefinition?: ContractDefinition;
}

export function ContractDefinitionForm({
  contractDefinition,
  ...props
}: Props) {
  const intl = useIntl();
  const formSubmitProps = useFormSubmit(contractDefinition);
  const contractDefinitionQuery = useContractDefinitions(
    {},
    { enabled: false },
  );
  const defaultContractDefinition =
    contractDefinition ?? props.fromContractDefinition;

  const RegisterSchema = Yup.object().shape({
    title: Yup.string().required(),
    description: Yup.string().required(),
    body: Yup.string().required(),
    appendix: Yup.string(),
    language: Yup.string().required(),
    name: Yup.string().required(),
  });

  const getDefaultValues = () => {
    return {
      title: defaultContractDefinition?.title ?? "",
      description: removeEOL(defaultContractDefinition?.description),
      body: removeEOL(defaultContractDefinition?.body),
      appendix: removeEOL(defaultContractDefinition?.appendix),
      name: "contract_definition",
      language: defaultContractDefinition?.language ?? "fr-fr",
    };
  };

  const methods = useForm({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues(),
  });

  const updateFormError = (
    errors: ServerSideErrorForm<DTOContractDefinition>,
  ) => {
    genericUpdateFormError(errors, methods.setError);
  };

  const onSubmit = (values: DTOContractDefinition) => {
    if (contractDefinition) {
      contractDefinitionQuery.methods.update(
        { id: contractDefinition.id, ...values },
        {
          onError: (error) => updateFormError(error.data),
          onSuccess: (updatedContractDefinition) =>
            props.afterSubmit?.(updatedContractDefinition),
        },
      );
    } else {
      contractDefinitionQuery.methods.create(values, {
        onError: (error) => updateFormError(error.data),
        onSuccess: (updatedContractDefinition) =>
          props.afterSubmit?.(updatedContractDefinition),
      });
    }
  };

  const bodyValue = methods.watch("body");
  const appendixValue = methods.watch("appendix");

  return (
    <Box padding={4}>
      <RHFProvider
        checkBeforeUnload={true}
        showSubmit={formSubmitProps.showSubmit}
        methods={methods}
        id="contract-definition-form"
        onSubmit={methods.handleSubmit(onSubmit)}
      >
        <RHFValuesChange
          autoSave={formSubmitProps.enableAutoSave}
          onSubmit={onSubmit}
        >
          <Grid container spacing={2}>
            <Grid size={12}>
              <Typography variant="subtitle2">
                {intl.formatMessage(messages.mainInformationTitle)}
              </Typography>
            </Grid>
            <Grid size={12}>
              <Alert severity="info">
                {intl.formatMessage(messages.informationText)}
              </Alert>
            </Grid>
            <Grid size={12}>
              <RHFTextField
                name="title"
                label={intl.formatMessage(messages.titleLabel)}
              />
            </Grid>
            <Grid size={12}>
              <RHFContractDefinitionLanguage name="language" />
            </Grid>
            <Grid size={12}>
              <RHFTextField
                name="description"
                multiline
                rows={5}
                label={intl.formatMessage(messages.descriptionLabel)}
              />
            </Grid>
            <Grid size={12}>
              <Typography
                variant="subtitle2"
                color={methods.formState.errors.body && "error"}
              >
                {intl.formatMessage(messages.bodyLabel)}
              </Typography>
            </Grid>
            <Grid size={12}>
              <MarkdownComponent
                data-testid="md-editor-body"
                value={bodyValue ?? ""}
                onChange={(markdown) => {
                  methods.setValue("body", markdown ?? "", {
                    shouldDirty: true,
                    shouldValidate: true,
                  });
                }}
              />
              <ErrorMessage
                errors={methods.formState.errors}
                name="body"
                render={(data) => (
                  <FormHelperText sx={{ marginLeft: "14px" }} error={true}>
                    {data.message}
                  </FormHelperText>
                )}
              />
            </Grid>
            <Grid size={12}>
              <Typography
                variant="subtitle2"
                color={methods.formState.errors.appendix && "error"}
              >
                {intl.formatMessage(messages.appendixLabel)}
              </Typography>
            </Grid>
            <Grid size={12}>
              <MarkdownComponent
                data-testid="md-editor-appendix"
                value={appendixValue ?? ""}
                onChange={(markdown) => {
                  methods.setValue("appendix", markdown ?? "", {
                    shouldDirty: true,
                    shouldValidate: true,
                  });
                }}
              />
              <ErrorMessage
                errors={methods.formState.errors}
                name="appendix"
                render={(data) => (
                  <FormHelperText sx={{ marginLeft: "14px" }} error={true}>
                    {data.message}
                  </FormHelperText>
                )}
              />
            </Grid>
          </Grid>
        </RHFValuesChange>
      </RHFProvider>
    </Box>
  );
}
