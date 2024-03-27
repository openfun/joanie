import * as React from "react";
import { GridColDef } from "@mui/x-data-grid";
import { defineMessages, useIntl } from "react-intl";
import {
  DefaultTableProps,
  TableComponent,
} from "@/components/presentational/table/TableComponent";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { usePaginatedTableResource } from "@/components/presentational/table/usePaginatedTableResource";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { PATH_ADMIN } from "@/utils/routes/path";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { EnrollmentListItem } from "@/services/api/models/Enrollment";
import {
  EnrollmentsListQuery,
  useEnrollments,
} from "@/hooks/useEnrollments/useEnrollments";
import { EnrollmentFilters } from "@/components/templates/enrollments/filters/EnrollmentFilters";

const messages = defineMessages({
  id: {
    id: "components.templates.enrollements.list.id",
    defaultMessage: "ID",
    description: "Label for the id header inside the table",
  },
  organizationTitle: {
    id: "components.templates.enrollements.list.organizationTitle",
    defaultMessage: "Organization",
    description: "Label for the organization header inside the table",
  },
  product: {
    id: "components.templates.enrollements.list.product",
    defaultMessage: "Product",
    description: "Label for the product header inside the table",
  },
  owner: {
    id: "components.templates.enrollements.list.owner",
    defaultMessage: "Owner",
    description: "Label for the owner header inside the table",
  },
  state: {
    id: "components.templates.enrollements.list.state",
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
      headerName: intl.formatMessage(messages.product),
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
