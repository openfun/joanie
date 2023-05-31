import * as React from "react";
import { useState } from "react";
import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { GridColDef, GridRenderCellParams } from "@mui/x-data-grid";
import { useDebouncedCallback } from "use-debounce";
import { TableComponent } from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { Course } from "@/services/api/models/Course";
import { CourseRun } from "@/services/api/models/CourseRun";
import { Maybe } from "@/types/utils";
import { useCourses } from "@/hooks/useCourses/useCourses";

const messages = defineMessages({
  codeHeader: {
    id: "components.templates.courses.list.codeHeader",
    defaultMessage: "Code",
    description: "Label for the code header inside the table  ",
  },
  title: {
    id: "components.templates.courses.list.title",
    defaultMessage: "Title",
    description: "Label for the title header inside the table  ",
  },
  state: {
    id: "components.templates.courses.list.state",
    defaultMessage: "State",
    description: "Label for the state header inside the table  ",
  },
});

export function CoursesList() {
  const intl = useIntl();
  const { push } = useRouter();
  const [search, setSearch] = useState<Maybe<string>>();
  const courses = useCourses({ search });

  const onSearch = useDebouncedCallback((term) => {
    setSearch(term);
  }, 300);

  const columns: GridColDef[] = [
    {
      field: "code",
      headerName: intl.formatMessage(messages.codeHeader),
      minWidth: 150,
      maxWidth: 250,
    },
    { field: "title", headerName: intl.formatMessage(messages.title), flex: 1 },
    {
      field: "state",
      headerName: intl.formatMessage(messages.state),
      renderCell: (params: GridRenderCellParams<any, CourseRun>) =>
        params.row.state?.text,
    },
  ];

  return (
    <TableComponent
      rows={courses.items}
      loading={courses.states.isLoading}
      columns={columns}
      columnBuffer={4}
      onSearch={onSearch}
      getEntityName={(course) => {
        return course.title;
      }}
      onEditClick={(course: Course) => {
        if (course.id) {
          push(PATH_ADMIN.courses.edit(course.id));
        }
      }}
      onRemoveClick={(course: Course) => courses.methods.delete(course.id)}
    />
  );
}
