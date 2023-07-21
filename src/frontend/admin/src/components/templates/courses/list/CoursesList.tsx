import * as React from "react";
import { useState } from "react";
import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { GridColDef } from "@mui/x-data-grid";
import { useDebouncedCallback } from "use-debounce";
import { TableComponent } from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { Course } from "@/services/api/models/Course";
import { Maybe } from "@/types/utils";
import { useCourses } from "@/hooks/useCourses/useCourses";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";

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
  const [query, setQuery] = useState<Maybe<string>>();
  const courses = useCourses({ query });

  const debouncedSetQuery = useDebouncedCallback((term) => {
    setQuery(term);
  }, 300);

  const columns: GridColDef<Course>[] = [
    {
      field: "code",
      headerName: intl.formatMessage(messages.codeHeader),
      minWidth: 150,
      maxWidth: 250,
    },
    {
      field: "title",
      headerName: intl.formatMessage(messages.title),
      flex: 1,
      renderCell: (cell) => {
        return (
          <CustomLink
            href={PATH_ADMIN.courses.edit(cell.row.id)}
            title={intl.formatMessage(commonTranslations.edit)}
          >
            {cell.row.title}
          </CustomLink>
        );
      },
    },
    {
      field: "state",
      headerName: intl.formatMessage(messages.state),
      renderCell: (params) => params.row.state?.text,
    },
  ];

  return (
    <SimpleCard>
      <TableComponent
        rows={courses.items}
        loading={courses.states.isLoading}
        columns={columns}
        columnBuffer={4}
        onSearch={debouncedSetQuery}
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
    </SimpleCard>
  );
}
