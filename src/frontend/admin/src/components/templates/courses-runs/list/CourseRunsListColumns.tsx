import { GridColDef, GridRenderCellParams } from "@mui/x-data-grid";
import * as React from "react";
import { defineMessages, IntlShape } from "react-intl";
import { CourseRun } from "@/services/api/models/CourseRun";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { formatShortDate } from "@/utils/dates";

const messages = defineMessages({
  courseCode: {
    id: "components.templates.courseRuns.list.courseCode",
    defaultMessage: "Course code",
    description: "Label for the course code header inside the table  ",
  },
  title: {
    id: "components.templates.courseRuns.list.title",
    defaultMessage: "Title",
    description: "Label for the title attribute header inside the table  ",
  },
  courseStart: {
    id: "components.templates.courseRuns.list.courseStart",
    defaultMessage: "Course start",
    description:
      "Label for the course start attribute header inside the table  ",
  },
  courseEnd: {
    id: "components.templates.courseRuns.list.courseEnd",
    defaultMessage: "Course end",
    description: "Label for the course end attribute header inside the table  ",
  },
  state: {
    id: "components.templates.courseRuns.list.state",
    defaultMessage: "State",
    description: "Label for the State attribute header inside the table  ",
  },
  isGradable: {
    id: "components.templates.courseRuns.list.isGradable",
    defaultMessage: "Is gradable",
    description: "Label for the isGradable attribute header inside the table  ",
  },
  clickToCopy: {
    id: "components.templates.courseRuns.list.clickToCopy",
    defaultMessage: "Click to copy this link",
    description: "Label for the click to copy tooltip",
  },
  successCopy: {
    id: "components.templates.courseRuns.list.successCopy",
    defaultMessage: "Link added to your clipboard",
    description: "Text for the success click to copy notification",
  },
});

export const getCoursesRunsListColumns = (
  intl: IntlShape,
): GridColDef<CourseRun>[] => {
  return [
    {
      field: "course_code",
      headerName: intl.formatMessage(messages.courseCode),
      flex: 1,
      renderCell: (cell) => {
        return (
          <CustomLink
            href={PATH_ADMIN.courses_run.edit(cell.row.id)}
            title={intl.formatMessage(commonTranslations.edit)}
          >
            {cell.row.course.code}
          </CustomLink>
        );
      },
    },
    {
      field: "title",
      headerName: intl.formatMessage(messages.title),
      minWidth: 200,
      flex: 1,
      renderCell: (cell) => {
        return (
          <CustomLink
            href={PATH_ADMIN.courses_run.edit(cell.row.id)}
            title={intl.formatMessage(commonTranslations.edit)}
          >
            {cell.row.title}
          </CustomLink>
        );
      },
    },
    {
      field: "start",
      headerName: intl.formatMessage(messages.courseStart),
      flex: 1,
      valueGetter: (value, row) =>
        row.start ? formatShortDate(row.start) : "",
    },
    {
      field: "end",
      headerName: intl.formatMessage(messages.courseEnd),
      flex: 1,
      valueGetter: (value, row) => {
        return row.end ? formatShortDate(row.end) : "";
      },
    },
    {
      field: "state",
      headerName: intl.formatMessage(messages.state),
      renderCell: (params: GridRenderCellParams<any, CourseRun>) =>
        params.row.state?.text,
    },
  ];
};
