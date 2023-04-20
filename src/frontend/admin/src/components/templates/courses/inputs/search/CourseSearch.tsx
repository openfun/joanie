import * as React from "react";
import { useState } from "react";
import {
  RHFAutocompleteSearchProps,
  RHFSearch,
} from "@/components/presentational/hook-form/RHFSearch";
import { Organization } from "@/services/api/models/Organization";
import { Maybe } from "@/types/utils";
import { Course } from "@/services/api/models/Course";
import { useCourses } from "@/hooks/useCourses/useCourses";

export function CourseSearch(props: RHFAutocompleteSearchProps<Course>) {
  const [search, setSearch] = useState("");
  const courses = useCourses({ search }, { enabled: search !== "" });

  return (
    <RHFSearch
      {...props}
      items={courses.items}
      loading={courses.states.fetching}
      onFilter={(term) => setSearch(term)}
      getOptionLabel={(option: Maybe<Organization>) => option?.title ?? ""}
      isOptionEqualToValue={(option, value) => option.code === value.code}
    />
  );
}
