import * as React from "react";
import { MutableRefObject, useEffect, useState } from "react";
import { FormProvider, UseFormReturn } from "react-hook-form";
import { FieldValues } from "react-hook-form/dist/types/fields";
import Box from "@mui/material/Box";
import { defineMessages, FormattedMessage, useIntl } from "react-intl";
import LoadingButton from "@mui/lab/LoadingButton";
import { useRouter } from "next/router";
import { AlertModal } from "@/components/presentational/modal/AlertModal";
import { useModal } from "@/components/presentational/modal/useModal";

const messages = defineMessages({
  dirtyModalTitle: {
    id: "components.presentational.hookForm.provider.dirtyModalTitle",
    defaultMessage: "Before you leave!",
    description: "Title for the dirty alert modal",
  },
  dirtyModalMessage: {
    id: "components.presentational.hookForm.provider.dirtyModalMessage",
    defaultMessage:
      "Changes in the form have been detected. Please submit the form or your changes will be lost.",
    description: "Message for the dirty alert modal",
  },
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
  checkBeforeUnload?: boolean;
}

export function RHFProvider<T extends FieldValues>({
  children,
  onSubmit,
  methods,
  actionButtons,
  showSubmit = true,
  isSubmitting = false,
  checkBeforeUnload = false,
  id,
}: Props<T>) {
  const intl = useIntl();
  const router = useRouter();
  const [nextUrl, setNextUrl] = useState<string>();
  const dirtyModal = useModal();

  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (!methods.formState.isDirty) {
        return;
      }

      event.preventDefault();
    };

    window.addEventListener("beforeunload", beforeUnload);
    return () => {
      window.removeEventListener("beforeunload", beforeUnload);
    };
  }, [methods.formState.isDirty]);

  useEffect(() => {
    const routeChangeStart = (url: string) => {
      if (
        !checkBeforeUnload ||
        !methods.formState.isDirty ||
        methods.formState.isSubmitted ||
        methods.formState.isSubmitting ||
        (nextUrl && dirtyModal.open)
      ) {
        return;
      }
      setNextUrl(url);
      dirtyModal.handleOpen();

      router.events.emit("routeChangeError");
      // eslint-disable-next-line @typescript-eslint/no-throw-literal
      throw `Form is dirty`;
    };
    router.events.on("routeChangeStart", routeChangeStart);
    return () => {
      router.events.off("routeChangeStart", routeChangeStart);
    };
  }, [
    nextUrl,
    methods.formState.isSubmitted,
    methods.formState.submitCount,
    methods.formState.isSubmitting,
    methods.formState.isSubmitting,
    methods.formState.isDirty,
    isSubmitting,
    dirtyModal.open,
  ]);

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
      <AlertModal
        open={dirtyModal.open}
        closeOnAccept={false}
        maxWidth="md"
        fullWidth={true}
        title={intl.formatMessage(messages.dirtyModalTitle)}
        message={intl.formatMessage(messages.dirtyModalMessage)}
        handleAccept={() => {
          if (!nextUrl) {
            return;
          }
          router.push(nextUrl);
        }}
        handleClose={() => {
          setNextUrl(undefined);
          dirtyModal.handleClose();
        }}
      />
    </FormProvider>
  );
}
