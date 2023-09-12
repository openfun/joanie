import * as React from "react";
import { useState } from "react";
import { useFormContext } from "react-hook-form";
import { defineMessages, useIntl } from "react-intl";
import {
  RHFAutocompleteSearchProps,
  RHFSearch,
} from "@/components/presentational/hook-form/RHFSearch";
import { Maybe } from "@/types/utils";
import { Course } from "@/services/api/models/Course";
import { useCourses } from "@/hooks/useCourses/useCourses";
import { CreateOrEditCourseModal } from "@/components/templates/courses/modals/CreateOrEditCourseModal";
import { useModal } from "@/components/presentational/modal/useModal";

const messages = defineMessages({
  searchLabel: {
    id: "components.templates.courses.inputs.search.CourseSearch.searchLabel",
    defaultMessage: "Course search",
    description: "Label for the CourseSearch component",
  },
});

export function CourseSearch(props: RHFAutocompleteSearchProps<Course>) {
  const intl = useIntl();
  const [query, setQuery] = useState("");
  const courses = useCourses({ query }, { enabled: query !== "" });
  const createModal = useModal();
  const form = useFormContext();
  return (
    <>
      <RHFSearch
        {...props}
        items={courses.items}
        label={props.label ?? intl.formatMessage(messages.searchLabel)}
        loading={courses.states.fetching}
        onAddClick={createModal.handleOpen}
        onFilter={setQuery}
        getOptionLabel={(option: Maybe<Course>) => option?.title ?? ""}
        isOptionEqualToValue={(option, value) => option.code === value.code}
      />
      <CreateOrEditCourseModal
        createModalUtils={createModal}
        afterSubmit={(course) => {
          createModal.handleClose();
          form.setValue(props.name, course);
        }}
      />
    </>
  );
}
