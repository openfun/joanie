import * as React from "react";
import { useState } from "react";
import { defineMessages, useIntl } from "react-intl";
import FormHelperText from "@mui/material/FormHelperText";
import Typography from "@mui/material/Typography";
import Grid2 from "@mui/material/Grid2";
import { useForm, useFormContext, useWatch } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import * as Yup from "yup";
import {
  Discount,
  DTODiscount,
  getDiscountLabel,
} from "@/services/api/models/Discount";
import { DiscountRepository } from "@/services/repositories/discount/DiscountRepository";
import { useDiscounts } from "@/hooks/useDiscounts/useDiscounts";
import {
  RHFAutocompleteSearchProps,
  RHFSearch,
} from "@/components/presentational/hook-form/RHFSearch";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { CustomModal } from "@/components/presentational/modal/Modal";
import { useModal } from "@/components/presentational/modal/useModal";

const messages = defineMessages({
  discountSelectLabel: {
    id: "components.presentational.discount.DiscountSelect.discountSelectLabel",
    defaultMessage: "Discount",
    description: "The label for the discount select",
  },
  noDiscountOption: {
    id: "components.presentational.discount.DiscountSelect.noDiscountOption",
    defaultMessage: "No discount",
    description: "The option for no discount",
  },
  createNewDiscountButton: {
    id: "components.presentational.discount.DiscountSelect.createNewDiscountButton",
    defaultMessage: "Create new discount",
    description: "The button to create a new discount",
  },
  addDiscountModalFormTitle: {
    id: "components.presentational.discount.DiscountSelect.addDiscountModalFormTitle",
    defaultMessage: "Add a discount",
    description: "Title for the add discount modal",
  },
  editDiscountModalFormTitle: {
    id: "components.presentational.discount.DiscountSelect.editDiscountModalFormTitle",
    defaultMessage: "Edit a discount",
    description: "Title for the edit discount modal",
  },
  amountLabel: {
    id: "components.presentational.discount.DiscountSelect.amountLabel",
    defaultMessage: "Amount (€)",
    description: "The label for the amount field",
  },
  rateLabel: {
    id: "components.presentational.discount.DiscountSelect.rateLabel",
    defaultMessage: "Rate (%)",
    description: "The label for the rate field",
  },
  cancelButton: {
    id: "components.presentational.discount.DiscountSelect.cancelButton",
    defaultMessage: "Cancel",
    description: "The cancel button",
  },
  createButton: {
    id: "components.presentational.discount.DiscountSelect.createButton",
    defaultMessage: "Create",
    description: "The create button",
  },
  discountHelperText: {
    id: "components.presentational.discount.DiscountSelect.discountHelperText",
    defaultMessage: "Select a discount or create a new one",
    description: "The helper text for the discount select",
  },
  discountRateHelperText: {
    id: "components.presentational.discount.DiscountSelect.discountRateHelperText",
    defaultMessage: "Enter a rate between 0 and 100",
    description: "The helper text for the rate field",
  },
  discountAmountHelperText: {
    id: "components.presentational.discount.DiscountSelect.discountAmountHelperText",
    defaultMessage: "Enter a fixed amount in euros",
    description: "The helper text for the amount field",
  },
  discountExclusiveHelperText: {
    id: "components.presentational.discount.DiscountSelect.discountExclusiveHelperText",
    defaultMessage: "You can only set either a rate or an amount, not both",
    description:
      "The helper text explaining that rate and amount are exclusive",
  },
});

export function DiscountSelect(
  props: RHFAutocompleteSearchProps<Discount["id"]>,
) {
  const { setValue } = useFormContext();
  const intl = useIntl();
  const discountModal = useModal();
  const [query, setQuery] = useState("");
  const discounts = useDiscounts({ query });
  const handleAddClick = () => {
    setQuery("");
    discountModal.handleOpen();
  };

  const Schema = Yup.object().shape({
    rate: Yup.number()
      .min(0)
      .max(100)
      .required()
      .nullable()
      .transform((curr, orig) => (orig === "" ? null : curr)),
    amount: Yup.number()
      .min(0)
      .required()
      .nullable()
      .transform((curr, orig) => (orig === "" ? null : curr)),
  });

  const form = useForm({
    resolver: yupResolver(Schema),
    defaultValues: {
      amount: null,
      rate: null,
    },
  });

  const handleCreateDiscount = async (dtoDiscount: DTODiscount) => {
    // Validate that either rate or amount is set, but not both
    if (
      (dtoDiscount.rate === null && dtoDiscount.amount === null) ||
      (dtoDiscount.rate !== null && dtoDiscount.amount !== null)
    ) {
      form.setError("amount", {
        type: "manual",
        message: intl.formatMessage(messages.discountExclusiveHelperText),
      });
      form.setError("rate", {
        type: "manual",
        message: intl.formatMessage(messages.discountExclusiveHelperText),
      });

      return;
    }

    try {
      if (dtoDiscount.rate !== null) {
        dtoDiscount.rate /= 100; // Convert to decimal
      }
      const createdDiscount = await DiscountRepository.create(dtoDiscount);
      await discounts.methods.create(createdDiscount);
      setValue(props.name, createdDiscount.id, {
        shouldTouch: true,
        shouldValidate: true,
      });
      await discounts.methods.refetch();
      discountModal.handleClose();
      form.reset();
    } catch (fetchError) {
      form.setError("root", {
        type: "manual",
        message: `Failed to create discount: ${fetchError}`,
      });
    }
  };

  return (
    <>
      <RHFSearch
        {...props}
        name={props.name}
        filterOptions={(x) => x}
        items={discounts.items.map((discount) => discount.id)}
        getOptionLabel={(discountID) =>
          getDiscountLabel(discounts.items.find((d) => d.id === discountID))
        }
        getOptionKey={(discountID) => discountID}
        loading={discounts.states.fetching}
        enableAdd={true}
        onAddClick={handleAddClick}
        onFilter={setQuery}
      />
      <FormHelperText>
        {props.helperText || intl.formatMessage(messages.discountHelperText)}
      </FormHelperText>

      <CustomModal
        fullWidth
        maxWidth="sm"
        title={intl.formatMessage(messages.addDiscountModalFormTitle)}
        {...discountModal}
        handleClose={() => {
          form.reset();
          discountModal.handleClose();
        }}
      >
        <RHFProvider
          methods={form}
          id="offering-rule-form"
          onSubmit={form.handleSubmit(async (values: DTODiscount) => {
            await handleCreateDiscount(values);
          })}
        >
          <Grid2 container spacing={2} sx={{ mt: 1 }}>
            <Grid2 size={12}>
              <Typography variant="body2" color="textSecondary">
                {intl.formatMessage(messages.discountExclusiveHelperText)}
              </Typography>
            </Grid2>
            <Grid2 size={12}>
              <RHFTextField
                name="rate"
                label={intl.formatMessage(messages.rateLabel)}
                type="number"
                fullWidth
                slotProps={{ htmlInput: { min: 0 } }}
                helperText={intl.formatMessage(messages.discountRateHelperText)}
                disabled={!!useWatch({ name: "amount", control: form.control })}
              />
            </Grid2>
            <Grid2 size={12}>
              <RHFTextField
                name="amount"
                label={intl.formatMessage(messages.amountLabel)}
                type="number"
                fullWidth
                slotProps={{ htmlInput: { min: 0 } }}
                helperText={intl.formatMessage(
                  messages.discountAmountHelperText,
                )}
                disabled={!!useWatch({ name: "rate", control: form.control })}
              />
            </Grid2>
            {form.formState.errors.root && (
              <Grid2 size={12}>
                <Typography color="error">
                  {form.formState.errors.root.message}
                </Typography>
              </Grid2>
            )}
          </Grid2>
        </RHFProvider>
      </CustomModal>
    </>
  );
}
