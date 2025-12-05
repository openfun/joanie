import * as React from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Grid2";
import { defineMessages, useIntl } from "react-intl";
import {
  MandatorySearchFilterProps,
  SearchFilters,
} from "@/components/presentational/filters/SearchFilters";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { Organization } from "@/services/api/models/Organization";
import { User } from "@/services/api/models/User";
import { OrganizationSearch } from "@/components/templates/organizations/inputs/search/OrganizationSearch";
import { UserSearch } from "@/components/templates/users/inputs/search/UserSearch";
import { RHFSelect } from "@/components/presentational/hook-form/RHFSelect";
import { entitiesInputLabel } from "@/translations/common/entitiesInputLabel";
import { BatchOrderListQuery } from "@/hooks/useBatchOrders/useBatchOrders";
import {
  BatchOrderPaymentMethodEnum,
  BatchOrderStatesEnum,
} from "@/services/api/models/BatchOrder";

const messages = defineMessages({
  searchPlaceholder: {
    id: "components.templates.batchOrders.filters.BatchOrderFilters.searchPlaceholder",
    description: "Text for the search input placeholder",
    defaultMessage: "Search by product, company, owner or organization name",
  },
  stateLabel: {
    id: "components.templates.batchOrders.filters.BatchOrderFilters.stateLabel",
    defaultMessage: "State",
    description: "Label for the batch order state filter",
  },
  paymentMethodLabel: {
    id: "components.templates.batchOrders.filters.BatchOrderFilters.paymentMethodLabel",
    defaultMessage: "Payment method",
    description: "Label for the batch order payment method filter",
  },
});

// Form values for filters UI
type FormValues = {
  organizations?: Organization[];
  owners?: User[];
  state?: string;
  payment_method?: string;
};

type Props = MandatorySearchFilterProps & {
  onFilter: (values: BatchOrderListQuery) => void;
};

export function BatchOrderFilters({ onFilter, ...searchFilterProps }: Props) {
  const intl = useIntl();

  const RegisterSchema = Yup.object().shape({
    state: Yup.string().nullable(),
    organizations: Yup.array<any, Organization>().nullable(),
    owners: Yup.array<any, User>().nullable(),
    payment_method: Yup.string().nullable(),
  });

  const methods = useForm<FormValues>({
    resolver: yupResolver(RegisterSchema),
    defaultValues: {
      organizations: [],
      owners: [],
      state: "",
      payment_method: "",
    },
  });

  const formValuesToFilterValues = (
    values: FormValues,
  ): BatchOrderListQuery => {
    return {
      organization_ids: values.organizations?.map((o) => o.id),
      owner_ids: values.owners?.map((u) => u.id),
      state: values.state,
      payment_method: values.payment_method,
    };
  };

  const onSubmit = (values: FormValues) => {
    onFilter(formValuesToFilterValues(values));
  };

  const stateOptions = Object.values(BatchOrderStatesEnum).map((value) => ({
    label: value,
    value,
  }));

  const paymentMethodOptions = Object.values(BatchOrderPaymentMethodEnum).map(
    (value) => ({
      label: value,
      value,
    }),
  );

  return (
    <SearchFilters
      {...searchFilterProps}
      searchInputPlaceholder={intl.formatMessage(messages.searchPlaceholder)}
      renderContent={() => (
        <RHFProvider
          id="batch-order-filters-main-form"
          showSubmit={false}
          methods={methods}
        >
          <RHFValuesChange
            debounceTime={200}
            updateUrl={true}
            formValuesToFilterValues={formValuesToFilterValues}
            onSubmit={onSubmit}
          >
            <Grid container mt={2} spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <RHFSelect
                  data-testid="select-batch-order-state-filter"
                  isFilterContext={true}
                  fullWidth={true}
                  name="state"
                  label={intl.formatMessage(messages.stateLabel)}
                  options={stateOptions}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <RHFSelect
                  data-testid="select-batch-order-payment-method-filter"
                  isFilterContext={true}
                  fullWidth={true}
                  name="payment_method"
                  label={intl.formatMessage(messages.paymentMethodLabel)}
                  options={paymentMethodOptions}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <OrganizationSearch
                  isFilterContext={true}
                  fullWidth={true}
                  multiple={true}
                  filterQueryName="organization_ids"
                  label={intl.formatMessage(entitiesInputLabel.organization)}
                  name="organizations"
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <UserSearch
                  isFilterContext={true}
                  fullWidth={true}
                  multiple={true}
                  label={intl.formatMessage(entitiesInputLabel.owner)}
                  filterQueryName="owner_ids"
                  name="owners"
                />
              </Grid>
            </Grid>
          </RHFValuesChange>
        </RHFProvider>
      )}
    />
  );
}
