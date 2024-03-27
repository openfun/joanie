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
import { CreateOrEditCourseModal } from "@/components/templates/courses/modals/CreateOrEditCourseModal";
import { useModal } from "@/components/presentational/modal/useModal";
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
  const form = useFormContext();
  const currentCourse: Nullable<Course> = form.getValues(props.name);
  const [query, setQuery] = useState("");
  const courses = useCoursesRuns({ query }, { enabled: query !== "" });
  const createModal = useModal();
  const editModal = useModal();
  return (
    <>
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
        onAddClick={createModal.handleOpen}
        onEditClick={editModal.handleOpen}
        onFilter={setQuery}
        getOptionLabel={(option: Maybe<CourseRun>) => option?.title ?? ""}
        isOptionEqualToValue={(option, value) => option.title === value.title}
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
