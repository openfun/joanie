import * as React from "react";
import { MutableRefObject } from "react";
import { FormProvider, UseFormReturn } from "react-hook-form";
import { FieldValues } from "react-hook-form/dist/types/fields";
import Box from "@mui/material/Box";
import { defineMessages, useIntl } from "react-intl";
import LoadingButton from "@mui/lab/LoadingButton";

const messages = defineMessages({
  submit: {
    id: "components.presentational.hookForm.provider.submit",
    defaultMessage: "Submit",
    description: "Submit label for submit button",
  },
});

interface Props<T extends FieldValues> {
  children: React.ReactNode;
  id?: string;
  methods: UseFormReturn<T>;
  onSubmit: VoidFunction;
  formRef?: MutableRefObject<HTMLFormElement | undefined>;
  isSubmitting?: boolean;
}

export function RHFProvider<T extends FieldValues>({
  children,
  onSubmit,
  methods,
  isSubmitting = false,
  id,
}: Props<T>) {
  const intl = useIntl();
  return (
    <FormProvider {...methods}>
      <form id={id} onSubmit={onSubmit}>
        {children}
        <Box mt={2} display="flex" justifyContent="flex-end">
          <LoadingButton
            loading={isSubmitting}
            variant="contained"
            type="submit"
          >
            {intl.formatMessage(messages.submit)}
          </LoadingButton>
        </Box>
      </form>
    </FormProvider>
  );
}
