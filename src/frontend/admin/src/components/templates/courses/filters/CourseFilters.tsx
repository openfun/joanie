import * as React from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Unstable_Grid2";
import { defineMessages, useIntl } from "react-intl";
import { OrganizationSearch } from "../../organizations/inputs/search/OrganizationSearch";
import { courseFormMessages } from "../form/translations";
import {
  MandatorySearchFilterProps,
  SearchFilters,
} from "@/components/presentational/filters/SearchFilters";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";

import { Organization } from "@/services/api/models/Organization";
import { CourseResourceQuery } from "@/hooks/useCourses/useCourses";

const messages = defineMessages({
  searchPlaceholder: {
    id: "components.templates.courses.filters.CourseFilters.searchPlaceholder",
    description: "Text for the search input placeholder",
    defaultMessage: "Search by title or code",
  },
});

type FormValues = {
  organizations?: Organization[];
};

type Props = MandatorySearchFilterProps & {
  onFilter: (values: CourseResourceQuery) => void;
};

export function CourseFilters({ onFilter, ...searchFilterProps }: Props) {
  const intl = useIntl();
  const getDefaultValues = () => {
    return {
      organizations: [],
    };
  };
  const RegisterSchema = Yup.object().shape({
    organizations: Yup.array<any, Organization>().nullable(),
  });

  const methods = useForm({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues() as any, // To not trigger type validation for default value
  });

  const formValuesToFilters = (values: FormValues) => {
    const filters: CourseResourceQuery = {
      organization_ids: values.organizations?.map((org) => org.id),
    };

    return filters;
  };

  const onSubmit = (values: FormValues) => {
    onFilter(formValuesToFilters(values));
  };

  return (
    <SearchFilters
      {...searchFilterProps}
      searchInputPlaceholder={intl.formatMessage(messages.searchPlaceholder)}
      renderContent={() => (
        <RHFProvider
          id="course-filter-form"
          showSubmit={false}
          methods={methods}
        >
          <RHFValuesChange
            debounceTime={200}
            updateUrl={true}
            formValuesToFilterValues={formValuesToFilters}
            useAnotherValueReference={true}
            onSubmit={onSubmit}
          >
            <Grid container mt={2} spacing={2}>
              <Grid xs={12}>
                <OrganizationSearch
                  enableAdd={false}
                  multiple={true}
                  filterQueryName="organization_ids"
                  isFilterContext={true}
                  name="organizations"
                  label={intl.formatMessage(
                    courseFormMessages.organizationsLabel,
                  )}
                />
              </Grid>
            </Grid>
          </RHFValuesChange>
        </RHFProvider>
      )}
    />
  );
}
