import * as React from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Grid2";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { defineMessages, useIntl } from "react-intl";

import { Voucher, DTOVoucher } from "@/services/api/models/Voucher";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { RHFCheckbox } from "@/components/presentational/hook-form/RHFCheckbox";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { useFormSubmit } from "@/hooks/form/useFormSubmit";
import { ServerSideErrorForm } from "@/types/utils";
import { genericUpdateFormError } from "@/utils/forms";
import { useVouchers } from "@/hooks/useVouchers/useVouchers";

const messages = defineMessages({
  generalSubtitle: {
    id: "components.templates.vouchers.form.generalSubtitle",
    defaultMessage: "General information",
    description: "Subtitle of the general section of the voucher form",
  },
  codeLabel: {
    id: "components.templates.vouchers.form.codeLabel",
    defaultMessage: "Voucher code",
    description: "Label for the code field",
  },
  offeringRuleIdLabel: {
    id: "components.templates.vouchers.form.offeringRuleIdLabel",
    defaultMessage: "Offering rule (ID)",
    description: "Label for the offering_rule_id field",
  },
  offeringRuleIdHelp: {
    id: "components.templates.vouchers.form.offeringRuleIdHelp",
    defaultMessage:
      "Identifier of the linked offering rule. Leave empty if none.",
    description: "Help text for the offering_rule_id field",
  },
  discountIdLabel: {
    id: "components.templates.vouchers.form.discountIdLabel",
    defaultMessage: "Discount (ID)",
    description: "Label for the discount_id field",
  },
  discountIdHelp: {
    id: "components.templates.vouchers.form.discountIdHelp",
    defaultMessage: "Identifier of the linked discount. Leave empty if none.",
    description: "Help text for the discount_id field",
  },
  multipleUseLabel: {
    id: "components.templates.vouchers.form.multipleUseLabel",
    defaultMessage: "Multiple uses by the same user",
    description: "Label for the multiple_use field",
  },
  multipleUseHelp: {
    id: "components.templates.vouchers.form.multipleUseHelp",
    defaultMessage:
      "If enabled, the same user can use this voucher multiple times.",
    description: "Help text for the multiple_use field",
  },
  multipleUsersLabel: {
    id: "components.templates.vouchers.form.multipleUsersLabel",
    defaultMessage: "Usable by multiple users",
    description: "Label for the multiple_users field",
  },
  multipleUsersHelp: {
    id: "components.templates.vouchers.form.multipleUsersHelp",
    defaultMessage: "If enabled, several distinct users can use this voucher.",
    description: "Help text for the multiple_users field",
  },
});

type Props = {
  afterSubmit?: (voucher: Voucher) => void;
  voucher?: Voucher;
  fromVoucher?: Voucher;
};

type FormValues = {
  code: string;
  offering_rule_id: string | null;
  discount_id: string | null;
  multiple_use: boolean;
  multiple_users: boolean;
};

export function VoucherForm({ voucher, fromVoucher, ...props }: Props) {
  const intl = useIntl();
  const vouchersQuery = useVouchers({}, { enabled: false });
  const formSubmitProps = useFormSubmit(voucher);

  const base = voucher ?? fromVoucher;

  const RegisterSchema = Yup.object().shape({
    code: Yup.string().required(),
    offering_rule_id: Yup.string().defined().nullable(),
    discount_id: Yup.string().defined().nullable(),
    multiple_use: Yup.boolean().required(),
    multiple_users: Yup.boolean().required(),
  });

  const getDefaultValues = (): FormValues => ({
    code: base?.code ?? "",
    offering_rule_id: base?.offering_rule?.id ?? null,
    discount_id: base?.discount?.id ?? null,
    multiple_use: base?.multiple_use ?? false,
    multiple_users: base?.multiple_users ?? false,
  });

  const methods = useForm<FormValues>({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues(),
  });

  const updateFormError = (errors: ServerSideErrorForm<FormValues>) => {
    genericUpdateFormError(errors, methods.setError);
  };

  const onSubmit = (values: FormValues) => {
    const payload: DTOVoucher = {
      code: values.code,
      offering_rule_id: values.offering_rule_id,
      discount_id: values.discount_id,
      multiple_use: values.multiple_use,
      multiple_users: values.multiple_users,
    };

    if (voucher) {
      const updatePayload = { id: voucher.id, ...payload } as DTOVoucher & {
        id: string;
      };
      vouchersQuery.methods.update(updatePayload, {
        onSuccess: (data) => props.afterSubmit?.(data),
        onError: (error) => updateFormError(error.data),
      });
    } else {
      vouchersQuery.methods.create(payload, {
        onSuccess: (data) => props.afterSubmit?.(data),
        onError: (error) => updateFormError(error.data),
      });
    }
  };

  return (
    <Box padding={4}>
      <RHFProvider
        checkBeforeUnload={true}
        showSubmit={formSubmitProps.showSubmit}
        methods={methods}
        isSubmitting={
          vouchersQuery.states.creating || vouchersQuery.states.updating
        }
        id="voucher-form"
        onSubmit={methods.handleSubmit(onSubmit)}
      >
        <RHFValuesChange
          autoSave={formSubmitProps.enableAutoSave}
          onSubmit={onSubmit}
        >
          <Grid container spacing={2}>
            <Grid size={12}>
              <Typography variant="subtitle2">
                {intl.formatMessage(messages.generalSubtitle)}
              </Typography>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <RHFTextField
                name="code"
                label={intl.formatMessage(messages.codeLabel)}
                required
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <RHFTextField
                name="offering_rule_id"
                label={intl.formatMessage(messages.offeringRuleIdLabel)}
                helperText={intl.formatMessage(messages.offeringRuleIdHelp)}
                placeholder="<offering-rule-id>"
              />
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <RHFTextField
                name="discount_id"
                label={intl.formatMessage(messages.discountIdLabel)}
                helperText={intl.formatMessage(messages.discountIdHelp)}
                placeholder="<discount-id>"
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
              <RHFCheckbox
                name="multiple_use"
                label={intl.formatMessage(messages.multipleUseLabel)}
                helperText={intl.formatMessage(messages.multipleUseHelp)}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
              <RHFCheckbox
                name="multiple_users"
                label={intl.formatMessage(messages.multipleUsersLabel)}
                helperText={intl.formatMessage(messages.multipleUsersHelp)}
              />
            </Grid>
          </Grid>
        </RHFValuesChange>
      </RHFProvider>
    </Box>
  );
}
