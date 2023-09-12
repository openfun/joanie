import * as React from "react";
import { useState } from "react";
import { useDebouncedCallback } from "use-debounce";
import { defineMessages, useIntl } from "react-intl";
import { Maybe } from "@/types/utils";
import ControlledSelect, {
  ControlledSelectProps,
} from "@/components/presentational/inputs/select/ControlledSelect";
import { Course } from "@/services/api/models/Course";
import { useCourses } from "@/hooks/useCourses/useCourses";
import { useModal } from "@/components/presentational/modal/useModal";
import { CreateOrEditCourseModal } from "@/components/templates/courses/modals/CreateOrEditCourseModal";

const messages = defineMessages({
  label: {
    id: "components.templates.courses.inputs.search.courseSearch.label",
    defaultMessage: "Search course",
    description: "Label for the controlled search course input",
  },
});

export function CourseControlledSearch(
  props: Omit<ControlledSelectProps<Course>, "options">,
) {
  const intl = useIntl();
  const [query, setQuery] = useState("");
  const courses = useCourses({ query });
  const debouncedSetSearch = useDebouncedCallback(setQuery, 300);
  const createModal = useModal();

  return (
    <>
      <ControlledSelect
        {...props}
        options={courses.items}
        loading={courses.states.fetching}
        onCreateClick={() => createModal.handleOpen()}
        onFilter={debouncedSetSearch}
        label={intl.formatMessage(messages.label)}
        getOptionLabel={(option: Maybe<Course>) => option?.title ?? ""}
        isOptionEqualToValue={(option, value) => option.code === value.code}
      />
      <CreateOrEditCourseModal
        createModalUtils={createModal}
        afterSubmit={(course) => {
          createModal.handleClose();
          props.onSelectItem?.(course);
        }}
      />
    </>
  );
}
