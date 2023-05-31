import { GridColDef, GridRenderCellParams } from "@mui/x-data-grid";
import * as React from "react";
import { defineMessages, IntlShape } from "react-intl";
import { Box, IconButton } from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { CourseRun } from "@/services/api/models/CourseRun";

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
});

export const getCoursesRunsListColumns = (
  intl: IntlShape
): GridColDef<any, CourseRun>[] => {
  return [
    {
      field: "title",
      headerName: intl.formatMessage(messages.title),
      minWidth: 300,
    },
    {
      field: "resource_link",
      headerName: intl.formatMessage(messages.resourceLink),
      minWidth: 400,
      flex: 1,
      renderCell: (params: GridRenderCellParams<any, CourseRun>) => {
        return (
          <Box
            sx={{
              "&:hover": {
                ".copy-resource-link": {
                  display: "block",
                },
              },
            }}
          >
            {params.row.resource_link}
            <IconButton
              onClick={() =>
                navigator.clipboard.writeText(params.row.resource_link)
              }
              sx={{ ml: 0.3 }}
            >
              <ContentCopyIcon
                className="copy-resource-link"
                fontSize="inherit"
                sx={{ display: "none", fontSize: "15px" }}
              />
            </IconButton>
          </Box>
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
