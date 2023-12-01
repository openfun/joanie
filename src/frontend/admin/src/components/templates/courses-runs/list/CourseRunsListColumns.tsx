import { GridColDef, GridRenderCellParams } from "@mui/x-data-grid";
import * as React from "react";
import { defineMessages, IntlShape } from "react-intl";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import { ProviderContext } from "notistack";
import { CourseRun } from "@/services/api/models/CourseRun";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { commonTranslations } from "@/translations/common/commonTranslations";

const messages = defineMessages({
  resourceLink: {
    id: "components.templates.courseRuns.list.resourceLink",
    defaultMessage: "Resource link",
    description: "Label for the resourceLink header inside the table  ",
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
  snackbar: ProviderContext,
): GridColDef<CourseRun>[] => {
  return [
    {
      field: "title",
      headerName: intl.formatMessage(messages.title),
      minWidth: 300,
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
      field: "resource_link",
      headerName: intl.formatMessage(messages.resourceLink),
      minWidth: 400,
      flex: 1,
      renderCell: (params) => {
        return (
          <Tooltip arrow title={intl.formatMessage(messages.clickToCopy)}>
            <Box
              onClick={() => {
                navigator.clipboard
                  .writeText(params.row.resource_link)
                  .then(() => {
                    snackbar.enqueueSnackbar(
                      intl.formatMessage(messages.successCopy),
                      {
                        variant: "success",
                        preventDuplicate: true,
                      },
                    );
                  });
              }}
              sx={{
                cursor: "pointer",
              }}
            >
              {params.row.resource_link}
            </Box>
          </Tooltip>
        );
      },
    },
    {
      field: "start",
      headerName: intl.formatMessage(messages.courseStart),
      flex: 1,
    },
    {
      field: "end",
      headerName: intl.formatMessage(messages.courseEnd),
      flex: 1,
    },
    {
      field: "state",
      headerName: intl.formatMessage(messages.state),
      renderCell: (params: GridRenderCellParams<any, CourseRun>) =>
        params.row.state?.text,
    },
  ];
};
