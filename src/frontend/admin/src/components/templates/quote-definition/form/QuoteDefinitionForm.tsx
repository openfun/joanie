import * as React from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Grid";
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
import { useQuoteDefinitions } from "@/hooks/useQuoteDefinitions/useQuoteDefinitions";
import {
  QuoteDefinition,
  QuoteDefinitionFormValues,
  QuoteDefinitionTemplate,
  DTOQuoteDefinition,
} from "@/services/api/models/QuoteDefinition";
import { MarkdownComponent } from "@/components/presentational/inputs/markdown/MardownComponent";
import { removeEOL } from "@/utils/string";
import { RHFQuoteDefinitionLanguage } from "@/components/templates/quote-definition/inputs/RHFQuoteDefinitionLanguage";
import RHFQuoteDefinitionName from "@/components/templates/quote-definition/inputs/RHFQuoteDefinitionName";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { useFormSubmit } from "@/hooks/form/useFormSubmit";

const messages = defineMessages({
  informationText: {
    id: "components.templates.quoteDefinitions.form.informationText",
    defaultMessage:
      "This is a quote template that will be used to issue quotes.",
    description: "Title for the information alert",
  },
  mainInformationTitle: {
    id: "components.templates.quoteDefinitions.form.mainInformationTitle",
    defaultMessage: "Main information's",
    description: "Title for the main information section",
  },
  titleLabel: {
    id: "components.templates.quoteDefinitions.form.titleLabel",
    defaultMessage: "Title",
    description: "Label for the title input",
  },
  languageLabel: {
    id: "components.templates.quoteDefinitions.form.languageLabel",
    defaultMessage: "Language",
    description: "Label for the language input",
  },
  descriptionLabel: {
    id: "components.templates.quoteDefinitions.form.descriptionLabel",
    defaultMessage: "Description",
    description: "Label for the name input",
  },
  bodyLabel: {
    id: "components.templates.quoteDefinitions.form.bodyLabel",
    defaultMessage: "Body",
    description: "Label for the body input",
  },
});

const FORM_VALIDATION_SCHEMA = Yup.object().shape({
  title: Yup.string().required(),
  description: Yup.string().required(),
  body: Yup.string().required(),
  language: Yup.string().required(),
  name: Yup.string()
    .oneOf([...Object.values(QuoteDefinitionTemplate), ""])
    .required(),
});

interface Props {
  afterSubmit?: (quoteDefinition: QuoteDefinition) => void;
  quoteDefinition?: QuoteDefinition;
  fromQuoteDefinition?: QuoteDefinition;
}

export function QuoteDefinitionForm({ quoteDefinition, ...props }: Props) {
  const intl = useIntl();
  const formSubmitProps = useFormSubmit(quoteDefinition);
  const quoteDefinitionQuery = useQuoteDefinitions({}, { enabled: false });
  const defaultQuoteDefinition = quoteDefinition ?? props.fromQuoteDefinition;

  const defaultValues: QuoteDefinitionFormValues = {
    title: defaultQuoteDefinition?.title ?? "",
    description: removeEOL(defaultQuoteDefinition?.description) ?? "",
    body: removeEOL(defaultQuoteDefinition?.body) ?? "",
    name: defaultQuoteDefinition?.name ?? "",
    language: defaultQuoteDefinition?.language ?? "fr-fr",
  };

  const methods = useForm({
    resolver: yupResolver(FORM_VALIDATION_SCHEMA),
    defaultValues,
  });

  const updateFormError = (errors: ServerSideErrorForm<DTOQuoteDefinition>) => {
    genericUpdateFormError(errors, methods.setError);
  };

  const onSubmit = (values: QuoteDefinitionFormValues) => {
    if (quoteDefinition) {
      quoteDefinitionQuery.methods.update(
        { id: quoteDefinition.id, ...values },
        {
          onError: (error) => updateFormError(error.data),
          onSuccess: (updatedQuoteDefinition) =>
            props.afterSubmit?.(updatedQuoteDefinition),
        },
      );
    } else {
      quoteDefinitionQuery.methods.create(values, {
        onError: (error) => updateFormError(error.data),
        onSuccess: (updatedQuoteDefinition) =>
          props.afterSubmit?.(updatedQuoteDefinition),
      });
    }
  };

  const bodyValue = methods.watch("body");

  return (
    <Box padding={4}>
      <RHFProvider
        checkBeforeUnload={true}
        showSubmit={formSubmitProps.showSubmit}
        methods={methods}
        id="quote-definition-form"
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
              <RHFQuoteDefinitionLanguage name="language" />
            </Grid>
            <Grid size={12}>
              <RHFQuoteDefinitionName name="name" />
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
          </Grid>
        </RHFValuesChange>
      </RHFProvider>
    </Box>
  );
}
