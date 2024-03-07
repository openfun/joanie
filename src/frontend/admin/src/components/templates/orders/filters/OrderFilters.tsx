import * as React from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Unstable_Grid2";
import { defineMessages, useIntl } from "react-intl";
import {
  MandatorySearchFilterProps,
  SearchFilters,
} from "@/components/presentational/filters/SearchFilters";
import { Course } from "@/services/api/models/Course";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { CourseSearch } from "@/components/templates/courses/inputs/search/CourseSearch";
import { Product } from "@/services/api/models/Product";
import { Organization } from "@/services/api/models/Organization";
import { User } from "@/services/api/models/User";
import { ProductSearch } from "@/components/templates/products/inputs/search/ProductSearch";
import { OrganizationSearch } from "@/components/templates/organizations/inputs/search/OrganizationSearch";
import { UserSearch } from "@/components/templates/users/inputs/search/UserSearch";
import { RHFOrderState } from "@/components/templates/orders/inputs/RHFOrderState";
import { entitiesInputLabel } from "@/translations/common/entitiesInputLabel";
import { OrderListQuery } from "@/hooks/useOrders/useOrders";

const messages = defineMessages({
  searchPlaceholder: {
    id: "components.templates.orders.filters.OrderFilters.searchPlaceholder",
    description: "Text for the search input placeholder",
    defaultMessage:
      "Search by product title, owner (full name or email), organization (code or title), course code",
  },
});

type FormValues = {
  product?: Product;
  course?: Course;
  organization?: Organization;
  owner?: User;
  products?: Product[];
  courses?: Course[];
  organizations?: Organization[];
  owners?: User[];
  state?: string;
};

type Props = MandatorySearchFilterProps & {
  onFilter: (values: OrderListQuery) => void;
};

export function OrderFilters({ onFilter, ...searchFilterProps }: Props) {
  const intl = useIntl();

  const getDefaultValues = () => {
    return {
      product: null,
      course: null,
      organization: null,
      owner: null,
      products: [],
      courses: [],
      organizations: [],
      owners: [],
      state: "",
    };
  };
  const RegisterSchema = Yup.object().shape({
    state: Yup.string().nullable(),
    products: Yup.array<any, Product>().nullable(),
    courses: Yup.array<any, Course>().nullable(),
    organizations: Yup.array<any, Organization>().nullable(),
    owners: Yup.array<any, User>().nullable(),
  });

  const methods = useForm({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues() as any, // To not trigger type validation for default value
  });

  const formValuesToFilterValues = (values: FormValues) => {
    const filters: OrderListQuery = {
      product_ids: values.products?.map((product) => product.id),
      course_ids: values.courses?.map((course) => course.id),
      organization_ids: values.organizations?.map(
        (organization) => organization.id,
      ),
      owner_ids: values.owners?.map((owner) => owner.id),
      state: values.state,
    };
    return filters;
  };

  const onSubmit = (values: FormValues) => {
    onFilter(formValuesToFilterValues(values));
  };

  return (
    <SearchFilters
      {...searchFilterProps}
      searchInputPlaceholder={intl.formatMessage(messages.searchPlaceholder)}
      renderContent={() => (
        <RHFProvider
          id="order-filters-main-form"
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
              <Grid xs={12}>
                <RHFOrderState
                  data-testid="select-order-state-filter"
                  isFilterContext={true}
                  fullWidth={true}
                  name="state"
                />
              </Grid>
              <Grid xs={12} sm={6}>
                <ProductSearch
                  isFilterContext={true}
                  multiple={true}
                  fullWidth={true}
                  filterQueryName="product_ids"
                  label={intl.formatMessage(entitiesInputLabel.product)}
                  name="products"
                />
              </Grid>
              <Grid xs={12} sm={6}>
                <CourseSearch
                  isFilterContext={true}
                  fullWidth={true}
                  multiple={true}
                  filterQueryName="course_ids"
                  label={intl.formatMessage(entitiesInputLabel.course)}
                  name="courses"
                />
              </Grid>
              <Grid xs={12} sm={6}>
                <OrganizationSearch
                  isFilterContext={true}
                  fullWidth={true}
                  multiple={true}
                  filterQueryName="organization_ids"
                  label={intl.formatMessage(entitiesInputLabel.organization)}
                  name="organizations"
                />
              </Grid>
              <Grid xs={12} sm={6}>
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
