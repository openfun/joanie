import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import Typography from "@mui/material/Typography";
import Grid2 from "@mui/material/Grid2";
import { useForm, useFormContext } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import * as Yup from "yup";
import { useState } from "react";
import {
  RHFAutocompleteSearchProps,
  RHFSearch,
} from "@/components/presentational/hook-form/RHFSearch";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { CustomModal } from "@/components/presentational/modal/Modal";
import { useModal } from "@/components/presentational/modal/useModal";
import RHFSwitch from "@/components/presentational/hook-form/RHFSwitch";
import { DiscountSelect } from "@/components/presentational/discount/DiscountSelect";
import { DTOVoucher, Voucher } from "@/services/api/models/Voucher";
import { useVouchers } from "@/hooks/useVouchers/useVouchers";
import { VoucherRepository } from "@/services/repositories/voucher/VoucherRepository";

const messages = defineMessages({
  voucherSelectLabel: {
    id: "components.presentational.voucher.VoucherSelect.voucherSelectLabel",
    defaultMessage: "Voucher",
    description: "The label for the voucher select",
  },
  noVoucherOption: {
    id: "components.presentational.voucher.VoucherSelect.noVoucherOption",
    defaultMessage: "No voucher",
    description: "The option for no voucher",
  },
  createNewVoucherButton: {
    id: "components.presentational.voucher.VoucherSelect.createNewVoucherButton",
    defaultMessage: "Create new voucher",
    description: "The button to create a new voucher",
  },
  addVoucherModalFormTitle: {
    id: "components.presentational.voucher.VoucherSelect.addVoucherModalFormTitle",
    defaultMessage: "Add a voucher",
    description: "Title for the add voucher modal",
  },
  editVoucherModalFormTitle: {
    id: "components.presentational.voucher.VoucherSelect.editVoucherModalFormTitle",
    defaultMessage: "Edit a voucher",
    description: "Title for the edit voucher modal",
  },
  codeLabel: {
    id: "components.presentational.voucher.VoucherSelect.codeLabel",
    defaultMessage: "Code",
    description: "The label for the code field",
  },
  multipleUseLabel: {
    id: "components.presentational.voucher.VoucherSelect.multipleUseLabel",
    defaultMessage: "Multiple use",
    description: "The label for the multiple use switch",
  },
  multipleUsersLabel: {
    id: "components.presentational.voucher.VoucherSelect.multipleUsersLabel",
    defaultMessage: "Multiple users",
    description: "The label for the multiple users switch",
  },
  discountLabel: {
    id: "components.templates.products.form.sections.OfferingRules.OfferingRuleForm.discountLabel",
    defaultMessage: "Discount",
    description: "The input label for the discount select",
  },
  cancelButton: {
    id: "components.presentational.voucher.VoucherSelect.cancelButton",
    defaultMessage: "Cancel",
    description: "The cancel button",
  },
  createButton: {
    id: "components.presentational.voucher.VoucherSelect.createButton",
    defaultMessage: "Create",
    description: "The create button",
  },
  voucherHelperText: {
    id: "components.presentational.voucher.VoucherSelect.voucherHelperText",
    defaultMessage: "Select a voucher or create a new one",
    description: "The helper text for the voucher select",
  },
  voucherRateHelperText: {
    id: "components.presentational.voucher.VoucherSelect.voucherRateHelperText",
    defaultMessage: "Enter a rate between 0 and 100",
    description: "The helper text for the rate field",
  },
  voucherAmountHelperText: {
    id: "components.presentational.voucher.VoucherSelect.voucherAmountHelperText",
    defaultMessage: "Enter a fixed amount in euros",
    description: "The helper text for the amount field",
  },
});

export function VoucherSelect(
  props: RHFAutocompleteSearchProps<Voucher["id"]>,
) {
  const { setValue } = useFormContext();
  const intl = useIntl();
  const voucherModal = useModal();
  const [query, setQuery] = useState("");
  const vouchers = useVouchers({ query });

  const handleAddClick = () => {
    setQuery("");
    voucherModal.handleOpen();
  };

  const Schema = Yup.object().shape({
    code: Yup.string().required(),
    multiple_use: Yup.boolean(),
    multiple_users: Yup.boolean(),
    discount_id: Yup.string().required(),
  });

  const form = useForm({
    resolver: yupResolver(Schema),
    defaultValues: {
      code: "",
      multiple_use: false,
      multiple_users: false,
      discount_id: "",
    },
  });

  const handleCreateVoucher = async (dtoVoucher: DTOVoucher) => {
    // Validation côté client: au moins un des champs "discount_id" ou "offering_rule_id"
    if (!dtoVoucher.discount_id) {
      form.setError("root", {
        type: "manual",
        message: "Réduction requise",
      });
      return;
    }

    try {
      const created = await VoucherRepository.create(dtoVoucher);
      await vouchers.methods.create(created);

      setValue(props.name, created.id, {
        shouldTouch: true,
        shouldValidate: true,
      });

      await vouchers.methods.refetch();
      voucherModal.handleClose();
      form.reset();
    } catch (fetchError) {
      form.setError("root", {
        type: "manual",
        message: `Échec de la création du voucher: ${fetchError}`,
      });
    }
  };

  return (
    <>
      <RHFSearch
        {...props}
        name={props.name}
        filterOptions={(x) => x}
        items={vouchers.items.map((v) => v.id)}
        getOptionLabel={(voucherID) =>
          vouchers.items.find((v) => v.id === voucherID)?.code || ""
        }
        getOptionKey={(voucherID) => voucherID}
        loading={vouchers.states.fetching}
        enableAdd={true}
        onAddClick={handleAddClick}
        onFilter={setQuery}
      />
      <CustomModal
        fullWidth
        maxWidth="sm"
        title={intl.formatMessage(messages.addVoucherModalFormTitle)}
        {...voucherModal}
        handleClose={() => {
          form.reset();
          voucherModal.handleClose();
        }}
      >
        <RHFProvider
          methods={form}
          id="offering-rule-form"
          onSubmit={form.handleSubmit(async (values: DTOVoucher) => {
            await handleCreateVoucher(values);
          })}
        >
          <Grid2 container>
            <Grid2 size={12}>
              <RHFTextField
                type="text"
                name="code"
                label={intl.formatMessage(messages.codeLabel)}
              />
              <Grid2 size={6}>
                <RHFSwitch
                  name="multiple_use"
                  label={intl.formatMessage(messages.multipleUseLabel)}
                />
              </Grid2>
              <Grid2 size={6}>
                <RHFSwitch
                  name="multiple_users"
                  label={intl.formatMessage(messages.multipleUsersLabel)}
                />
              </Grid2>
            </Grid2>
            {form.formState.errors.root && (
              <Grid2 size={12}>
                <Typography color="error">
                  {form.formState.errors.root.message}
                </Typography>
              </Grid2>
            )}
          </Grid2>
          <Grid2 size={12}>
            <DiscountSelect
              name="discount_id"
              label={intl.formatMessage(messages.discountLabel)}
            />
          </Grid2>
        </RHFProvider>
      </CustomModal>
    </>
  );
}
