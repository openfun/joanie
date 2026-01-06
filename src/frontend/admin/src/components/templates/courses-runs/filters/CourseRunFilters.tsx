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
import { Course } from "@/services/api/models/Course";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { CourseSearch } from "@/components/templates/courses/inputs/search/CourseSearch";
import { RHFSelectCourseRunState } from "@/components/templates/courses-runs/input/RHFSelectCourseRunState";
import RHFRadioGroup from "@/components/presentational/hook-form/RHFRadioGroup";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { entitiesInputLabel } from "@/translations/common/entitiesInputLabel";
import { courseRunFormMessages } from "@/components/templates/courses-runs/form/translations";
import { CourseRunResourcesQuery } from "@/hooks/useCourseRun/useCourseRun";
import { Organization } from "@/services/api/models/Organization";
import { courseFormMessages } from "@/components/templates/courses/form/translations";
import { OrganizationSearch } from "@/components/templates/organizations/inputs/search/OrganizationSearch";

const messages = defineMessages({
  searchPlaceholder: {
    id: "components.templates.coursesRuns.filters.CourseRunFilters.searchPlaceholder",
    description: "Text for the search input placeholder",
    defaultMessage: "Search by title or resource link",
  },
});

type FormValues = {
  course: Course;
  courses: Course[];
  organizations: Organization[];
  state: string;
  is_gradable: boolean | "none";
  is_listed: boolean | "none";
};

type Props = MandatorySearchFilterProps & {
  onFilter: (values: CourseRunResourcesQuery) => void;
};

export function CourseRunFilters({ onFilter, ...searchFilterProps }: Props) {
  const intl = useIntl();

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

  const getDefaultValues = () => {
    return {
      course: null,
      courses: [],
      organizations: [],
      state: "",
      is_gradable: "none",
      is_listed: "none",
    };
  };

  const RegisterSchema = Yup.object().shape({
    course: Yup.mixed<Course>().nullable(),
    courses: Yup.array<any, Course>().nullable(),
    organizations: Yup.array<any, Organization>().nullable(),
    state: Yup.string().nullable(),
    is_gradable: Yup.mixed().nullable(),
    is_listed: Yup.mixed().nullable(),
  });

  const methods = useForm({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues() as any, // To not trigger type validation for default value
  });

  const formValuesToFilterValues = (
    values: FormValues,
  ): CourseRunResourcesQuery => {
    return {
      course_ids: values.courses.map((course) => course.id),
      organization_ids: values.organizations.map(
        (organization) => organization.id,
      ),
      state: values.state,
      is_listed: values.is_listed !== "none" ? values.is_listed : undefined,
      is_gradable:
        values.is_gradable !== "none" ? values.is_gradable : undefined,
    };
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
          id="course-run-filters-form"
          showSubmit={false}
          methods={methods}
        >
          <RHFValuesChange
            updateUrl={true}
            formValuesToFilterValues={formValuesToFilterValues}
            debounceTime={200}
            onSubmit={onSubmit}
          >
            <Grid container mt={2} spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <CourseSearch
                  isFilterContext={true}
                  multiple={true}
                  fullWidth={true}
                  filterQueryName="course_ids"
                  label={intl.formatMessage(entitiesInputLabel.course)}
                  name="courses"
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <OrganizationSearch
                  enableAdd={false}
                  multiple={true}
                  isFilterContext={true}
                  filterQueryName="organization_ids"
                  name="organizations"
                  label={intl.formatMessage(
                    courseFormMessages.organizationsLabel,
                  )}
                />
              </Grid>
              <Grid size={12}>
                <RHFSelectCourseRunState
                  data-testid="select-course-run-state"
                  isFilterContext={true}
                  fullWidth={true}
                  name="state"
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <RHFRadioGroup
                  row
                  data-testid="course-run-isListed-filter"
                  getValueLabel={getTrueFalseLabel}
                  options={trueFalseOptions}
                  isFilterContext={true}
                  label={intl.formatMessage(
                    courseRunFormMessages.isListedLabel,
                  )}
                  name="is_listed"
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <RHFRadioGroup
                  row
                  data-testid="course-run-isGradable-filter"
                  getValueLabel={getTrueFalseLabel}
                  options={trueFalseOptions}
                  isFilterContext={true}
                  label={intl.formatMessage(
                    courseRunFormMessages.isGradableLabel,
                  )}
                  name="is_gradable"
                />
              </Grid>
            </Grid>
          </RHFValuesChange>
        </RHFProvider>
      )}
    />
  );
}
