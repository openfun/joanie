import * as React from "react";
import { MutableRefObject } from "react";
import { FormProvider, UseFormReturn } from "react-hook-form";
import { FieldValues } from "react-hook-form/dist/types/fields";
import Box from "@mui/material/Box";
import { defineMessages, FormattedMessage } from "react-intl";
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
  actionButtons?: React.ReactNode;
  onSubmit?: VoidFunction;
  formRef?: MutableRefObject<HTMLFormElement | undefined>;
  isSubmitting?: boolean;
  showSubmit?: boolean;
}

export function RHFProvider<T extends FieldValues>({
  children,
  onSubmit,
  methods,
  actionButtons,
  showSubmit = true,
  isSubmitting = false,
  id,
}: Props<T>) {
  return (
    <FormProvider {...methods}>
      <form
        id={id}
        onSubmit={(event) => {
          event.stopPropagation();
          event.preventDefault();
          onSubmit?.();
        }}
      >
        {children}
        {(showSubmit || actionButtons) && (
          <Box
            gap={2}
            mt={2}
            display="flex"
            flexDirection="row"
            justifyContent="flex-end"
          >
            {actionButtons}
            {showSubmit && (
              <LoadingButton
                data-testid={id ? `submit-button-${id}` : "submit-button"}
                loading={isSubmitting}
                variant="contained"
                type="submit"
              >
                <FormattedMessage {...messages.submit} />
              </LoadingButton>
            )}
          </Box>
        )}
      </form>
    </FormProvider>
  );
}
