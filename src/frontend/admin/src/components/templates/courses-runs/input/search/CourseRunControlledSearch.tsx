import * as React from "react";
import { useState } from "react";
import { useDebouncedCallback } from "use-debounce";
import { defineMessages, useIntl } from "react-intl";
import TuneIcon from "@mui/icons-material/Tune";
import Box from "@mui/material/Box";
import { DatePicker } from "@mui/x-date-pickers";
import Badge from "@mui/material/Badge";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import { Maybe } from "@/types/utils";
import ControlledSelect, {
  ControlledSelectProps,
} from "@/components/presentational/inputs/select/ControlledSelect";
import { useModal } from "@/components/presentational/modal/useModal";
import { CourseRun } from "@/services/api/models/CourseRun";
import {
  CourseRunResourcesQuery,
  useCoursesRuns,
} from "@/hooks/useCourseRun/useCourseRun";
import ButtonPopover from "@/components/presentational/button/popover/ButtonPopover";
import { BasicSelect } from "@/components/presentational/inputs/select/BasicSelect";

const messages = defineMessages({
  label: {
    id: "components.templates.courses.inputs.search.courseSearch.label",
    defaultMessage: "Search course run",
    description: "Label for the controlled search course input",
  },
  filtersPopoverTitle: {
    id: "components.templates.courses.inputs.search.courseSearch.filtersPopoverTitle",
    defaultMessage: "Course run filters",
    description: "Title for the filters popover",
  },
  startDateFilterLabel: {
    id: "components.templates.courses.inputs.search.courseSearch.startDateFilterLabel",
    defaultMessage: "Course run start date",
    description: "Label for the start date filter",
  },
  statusFilterLabel: {
    id: "components.templates.courses.inputs.search.courseSearch.statusFilterLabel",
    defaultMessage: "Course run status",
    description: "Label for the start date filter",
  },
});

type Props = Omit<ControlledSelectProps<CourseRun>, "options"> & {
  courseId?: string;
};

export function CourseRunControlledSearch({ courseId, ...props }: Props) {
  const intl = useIntl();
  const [filters, setFilters] = useState<CourseRunResourcesQuery>({
    start: null,
    state: "",
  });
  const courseRuns = useCoursesRuns({ ...filters, courseId });
  const updateFilters = (newFilters: CourseRunResourcesQuery) => {
    setFilters((prevState) => ({
      ...prevState,
      ...newFilters,
    }));
  };
  const debouncedSetSearch = useDebouncedCallback((term: string) => {
    updateFilters({ query: term });
  }, 300);
  const createModal = useModal();

  return (
    <ControlledSelect
      {...props}
      options={courseRuns.items}
      leftIcons={
        <Badge
          invisible={
            (filters.state == null || filters.state === "") &&
            filters.start == null
          }
          badgeContent=""
          variant="dot"
          color="warning"
          sx={{
            "& .MuiBadge-badge": {
              right: 5,
              top: 6,
            },
          }}
        >
          <ButtonPopover
            button={
              <IconButton size="small">
                <TuneIcon color="primary" />
              </IconButton>
            }
          >
            <Box p={2}>
              <Stack gap={2}>
                <Typography variant="subtitle2">
                  {intl.formatMessage(messages.filtersPopoverTitle)}
                </Typography>
                <DatePicker
                  slotProps={{ actionBar: { actions: ["clear"] } }}
                  label={intl.formatMessage(messages.startDateFilterLabel)}
                  value={filters.start ? new Date(filters?.start) : null}
                  onChange={(newValue) => {
                    updateFilters({
                      start: newValue ? new Date(newValue).toISOString() : null,
                    });
                  }}
                />
                <BasicSelect
                  value={filters.state}
                  label={intl.formatMessage(messages.statusFilterLabel)}
                  onSelect={(newState) => updateFilters({ state: newState })}
                  options={[
                    { label: "A", value: "AA" },
                    { label: "B", value: "BB" },
                  ]}
                />
              </Stack>
            </Box>
          </ButtonPopover>
        </Badge>
      }
      filterOptions={(x) => x}
      loading={courseRuns.states.isLoading}
      onCreateClick={() => createModal.handleOpen()}
      onFilter={debouncedSetSearch}
      label={intl.formatMessage(messages.label)}
      getOptionLabel={(option: Maybe<CourseRun>) => option?.title ?? ""}
      isOptionEqualToValue={(option, value) => option.title === value.title}
    />
  );
}
