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
import { User } from "@/services/api/models/User";
import { UserSearch } from "@/components/templates/users/inputs/search/UserSearch";
import { entitiesInputLabel } from "@/translations/common/entitiesInputLabel";
import { OrderListQuery } from "@/hooks/useOrders/useOrders";
import { CourseRun } from "@/services/api/models/CourseRun";
import { EnrollmentsListQuery } from "@/hooks/useEnrollments/useEnrollments";
import { RHFCourseRunSearch } from "@/components/templates/courses-runs/input/search/RHFCourseRunSearch";
import RHFRadioGroup from "@/components/presentational/hook-form/RHFRadioGroup";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { RHFSelectEnrollmentState } from "@/components/templates/enrollments/inputs/RHFSelectEnrollmentState";

const messages = defineMessages({
  searchPlaceholder: {
    id: "components.templates.enrollments.filters.EnrollmentFilters.searchPlaceholder",
    description: "Text for the search input placeholder",
    defaultMessage: "Search by course run title, resource link, course code",
  },
  isActiveLabel: {
    id: "components.templates.enrollments.filters.EnrollmentFilters.isActiveLabel",
    description:
      "Label for the is listed checkbox inside the Enrollment filters component",
    defaultMessage: "Is active",
  },
});

type FormValues = {
  courseRuns: CourseRun[];
  users: User[];
  is_active: boolean | "none";
  state: string;
};

type Props = MandatorySearchFilterProps & {
  onFilter: (values: OrderListQuery) => void;
};

export function EnrollmentFilters({ onFilter, ...searchFilterProps }: Props) {
  const intl = useIntl();

  const getDefaultValues = () => {
    return {
      courseRuns: [],
      users: [],
      is_active: "none",
      state: "",
    };
  };
  const RegisterSchema = Yup.object().shape({
    courseRuns: Yup.array<any, CourseRun>().min(0).optional(),
    is_active: Yup.mixed().nullable(),
    state: Yup.string().nullable(),
    users: Yup.array<any, User>().min(0).optional(),
  });

  const methods = useForm({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues() as any, // To not trigger type validation for default value
  });

  const formValuesToFilterValues = (values: FormValues) => {
    const filters: EnrollmentsListQuery = {
      course_run_ids: values.courseRuns?.map((courseRun) => courseRun.id),
      user_ids: values.users?.map((user) => user.id),
      is_active: values.is_active !== "none" ? values.is_active : undefined,
      state: values.state,
    };
    return filters;
  };

  const onSubmit = (values: FormValues) => {
    onFilter(formValuesToFilterValues(values));
  };

  const trueFalseOptions = [
    { label: intl.formatMessage(commonTranslations.none), value: "none" },
    { label: intl.formatMessage(commonTranslations.yes), value: true },
    { label: intl.formatMessage(commonTranslations.no), value: false },
  ];

  const getTrueFalseLabel = (value: string): string => {
    if (value === "") {
      return "";
    }

    return intl.formatMessage(
      value === "true" ? commonTranslations.yes : commonTranslations.no,
    );
  };

  return (
    <SearchFilters
      {...searchFilterProps}
      searchInputPlaceholder={intl.formatMessage(messages.searchPlaceholder)}
      renderContent={() => (
        <RHFProvider
          id="enrollment-filters-main-form"
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
                <RHFCourseRunSearch
                  isFilterContext={true}
                  fullWidth={true}
                  multiple={true}
                  filterQueryName="course_run_ids"
                  name="courseRuns"
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <UserSearch
                  isFilterContext={true}
                  multiple={true}
                  fullWidth={true}
                  filterQueryName="user_ids"
                  label={intl.formatMessage(entitiesInputLabel.owner)}
                  name="users"
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <RHFRadioGroup
                  row
                  data-testid="enrollment-isActive-filter"
                  getValueLabel={getTrueFalseLabel}
                  options={trueFalseOptions}
                  isFilterContext={true}
                  filterQueryName="is_active"
                  label={intl.formatMessage(messages.isActiveLabel)}
                  name="is_active"
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <RHFSelectEnrollmentState
                  data-testid="select-enrollment-state"
                  isFilterContext={true}
                  fullWidth={true}
                  name="state"
                />
              </Grid>
            </Grid>
          </RHFValuesChange>
        </RHFProvider>
      )}
    />
  );
}
