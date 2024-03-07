import * as React from "react";
import { useState } from "react";
import { useFormContext } from "react-hook-form";
import { defineMessages, useIntl } from "react-intl";
import {
  RHFAutocompleteSearchProps,
  RHFSearch,
} from "@/components/presentational/hook-form/RHFSearch";
import { Maybe, Nullable } from "@/types/utils";
import { Course } from "@/services/api/models/Course";
import { useCourses } from "@/hooks/useCourses/useCourses";
import { CreateOrEditCourseModal } from "@/components/templates/courses/modals/CreateOrEditCourseModal";
import { useModal } from "@/components/presentational/modal/useModal";
import { CourseRepository } from "@/services/repositories/courses/CoursesRepository";

const messages = defineMessages({
  searchLabel: {
    id: "components.templates.courses.inputs.search.CourseSearch.searchLabel",
    defaultMessage: "Course search",
    description: "Label for the CourseSearch component",
  },
});

export function CourseSearch(props: RHFAutocompleteSearchProps<Course>) {
  const intl = useIntl();
  const form = useFormContext();
  const currentCourse: Nullable<Course> = form.getValues(props.name);
  const [query, setQuery] = useState("");
  const courses = useCourses({ query }, { enabled: query !== "" });
  const createModal = useModal();
  const editModal = useModal();
  return (
    <>
      <RHFSearch
        {...props}
        data-testid="course-runs-search"
        findFilterValue={async (values) => {
          const request = await CourseRepository.getAll({ ids: values });
          return request.results;
        }}
        items={courses.items}
        label={props.label ?? intl.formatMessage(messages.searchLabel)}
        loading={courses.states.fetching}
        onAddClick={createModal.handleOpen}
        onEditClick={editModal.handleOpen}
        onFilter={setQuery}
        getOptionLabel={(option: Maybe<Course>) => option?.title ?? ""}
        isOptionEqualToValue={(option, value) => option.code === value.code}
      />
      <CreateOrEditCourseModal
        createModalUtils={createModal}
        editModalUtils={editModal}
        courseId={
          currentCourse && props.enableEdit ? currentCourse.id : undefined
        }
        afterSubmit={(course) => {
          createModal.handleClose();
          editModal.handleClose();
          form.setValue(props.name, course);
        }}
      />
    </>
  );
}
