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
import { BatchOrderStatesEnum } from "@/services/api/models/BatchOrder";

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
});

// Form values for filters UI
type FormValues = {
  organizations?: Organization[];
  owners?: User[];
  state?: string;
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
  });

  const methods = useForm<FormValues>({
    resolver: yupResolver(RegisterSchema),
    defaultValues: { organizations: [], owners: [], state: "" },
  });

  const formValuesToFilterValues = (
    values: FormValues,
  ): BatchOrderListQuery => {
    return {
      organization_ids: values.organizations?.map((o) => o.id),
      owner_ids: values.owners?.map((u) => u.id),
      state: values.state,
    };
  };

  const onSubmit = (values: FormValues) => {
    onFilter(formValuesToFilterValues(values));
  };

  const stateOptions = Object.values(BatchOrderStatesEnum).map((value) => ({
    label: value,
    value,
  }));

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
              <Grid size={12}>
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
