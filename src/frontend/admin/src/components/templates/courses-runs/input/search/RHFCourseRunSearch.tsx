import * as React from "react";
import { useState } from "react";
import { defineMessages, useIntl } from "react-intl";
import {
  RHFAutocompleteSearchProps,
  RHFSearch,
} from "@/components/presentational/hook-form/RHFSearch";
import { Maybe } from "@/types/utils";
import { useCoursesRuns } from "@/hooks/useCourseRun/useCourseRun";
import { CourseRun } from "@/services/api/models/CourseRun";
import { CoursesRunsRepository } from "@/services/repositories/courses-runs/CoursesRunsRepository";

const messages = defineMessages({
  searchLabel: {
    id: "components.templates.courses.inputs.search.CourseSearch.searchLabel",
    defaultMessage: "Course search",
    description: "Label for the CourseSearch component",
  },
});

export function RHFCourseRunSearch(
  props: RHFAutocompleteSearchProps<CourseRun>,
) {
  const intl = useIntl();
  const [query, setQuery] = useState("");
  const courses = useCoursesRuns({ query }, { enabled: query !== "" });

  return (
    <RHFSearch
      {...props}
      data-testid="course-runs-search-input"
      findFilterValue={async (values) => {
        const request = await CoursesRunsRepository.getAll({ ids: values });
        return request.results;
      }}
      items={courses.items}
      label={props.label ?? intl.formatMessage(messages.searchLabel)}
      loading={courses.states.fetching}
      onFilter={setQuery}
      getOptionLabel={(option: Maybe<CourseRun>) => option?.title ?? ""}
      isOptionEqualToValue={(option, value) => option.title === value.title}
    />
  );
}
