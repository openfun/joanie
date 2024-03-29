import * as React from "react";
import { GridColDef } from "@mui/x-data-grid";
import { defineMessages, FormattedMessage, useIntl } from "react-intl";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import {
  DefaultTableProps,
  TableComponent,
} from "@/components/presentational/table/TableComponent";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { usePaginatedTableResource } from "@/components/presentational/table/usePaginatedTableResource";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { PATH_ADMIN } from "@/utils/routes/path";
import { commonTranslations } from "@/translations/common/commonTranslations";
import {
  EnrollmentListItem,
  EnrollmentState,
} from "@/services/api/models/Enrollment";
import {
  EnrollmentsListQuery,
  useEnrollments,
} from "@/hooks/useEnrollments/useEnrollments";
import { EnrollmentFilters } from "@/components/templates/enrollments/filters/EnrollmentFilters";
import { enrollmentStateMessages } from "@/translations/enrollments/enrollment-state";

const messages = defineMessages({
  courseRun: {
    id: "components.templates.enrollments.courseRun.id",
    defaultMessage: "Course run",
    description: "Label for the course run header inside the table",
  },
  isActive: {
    id: "components.templates.enrollments.list.isActive",
    defaultMessage: "Is active",
    description: "Label for the is active header inside the table",
  },
  owner: {
    id: "components.templates.enrollments.list.owner",
    defaultMessage: "Owner",
    description: "Label for the owner header inside the table",
  },
  state: {
    id: "components.templates.enrollments.list.state",
    defaultMessage: "State",
    description: "Label for the state header inside the table",
  },
});

type Props = DefaultTableProps<EnrollmentListItem>;

export function EnrollmentsList(props: Props) {
  const intl = useIntl();

  const paginatedResource = usePaginatedTableResource<
    EnrollmentListItem,
    EnrollmentsListQuery
  >({
    useResource: useEnrollments,
    changeUrlOnPageChange: props.changeUrlOnPageChange,
  });

  const columns: GridColDef[] = [
    {
      field: "title",
      headerName: intl.formatMessage(messages.courseRun),
      renderCell: (cell) => {
        return (
          <CustomLink
            href={PATH_ADMIN.enrollments.view(cell.row.id)}
            title={intl.formatMessage(commonTranslations.view)}
          >
            {cell.row.course_run.title}
          </CustomLink>
        );
      },
      flex: 1,
    },
    {
      field: "user_name",
      headerName: intl.formatMessage(messages.owner),
      renderCell: (cell) => {
        return (
          <CustomLink
            href={PATH_ADMIN.enrollments.view(cell.row.id)}
            title={intl.formatMessage(commonTranslations.view)}
          >
            {cell.row.user_name}
          </CustomLink>
        );
      },
      flex: 1,
    },
    {
      field: "is_active",
      headerName: intl.formatMessage(messages.isActive),
      renderCell: (cell) => {
        return (
          <CustomLink
            href={PATH_ADMIN.enrollments.view(cell.row.id)}
            title={intl.formatMessage(commonTranslations.view)}
          >
            <Checkbox checked={cell.row.is_active} />
          </CustomLink>
        );
      },
      flex: 1,
    },
    {
      field: "state",
      headerName: intl.formatMessage(messages.state),
      renderCell: (cell) => {
        return (
          <Chip
            size="small"
            color={
              cell.row.state === EnrollmentState.FAILED ? "error" : undefined
            }
            label={
              <FormattedMessage
                {...enrollmentStateMessages[cell.row.state as EnrollmentState]}
              />
            }
          />
        );
      },
      flex: 1,
    },
  ];

  return (
    <SimpleCard>
      <TableComponent
        {...paginatedResource.tableProps}
        {...props}
        filters={<EnrollmentFilters {...paginatedResource.filtersProps} />}
        enableEdit={false}
        columns={columns}
        columnBuffer={5}
        getEntityName={(enrollment) => {
          return enrollment.course_run.title;
        }}
      />
    </SimpleCard>
  );
}
