import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { GridColDef } from "@mui/x-data-grid";
import CopyAllIcon from "@mui/icons-material/CopyAll";
import {
  DefaultTableProps,
  TableComponent,
} from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CourseRun } from "@/services/api/models/CourseRun";
import { getCoursesRunsListColumns } from "@/components/templates/courses-runs/list/CourseRunsListColumns";
import {
  CourseRunResourcesQuery,
  useCoursesRuns,
} from "@/hooks/useCourseRun/useCourseRun";
import { usePaginatedTableResource } from "@/components/presentational/table/usePaginatedTableResource";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";
import { CourseRunFilters } from "@/components/templates/courses-runs/filters/CourseRunFilters";

const messages = defineMessages({
  copyResourceLink: {
    id: "components.templates.courseRuns.list.copyResourceLink",
    defaultMessage: "Copy the resource link",
    description:
      "Label for the copy the resource link option inside the more button",
  },
});

type Props = DefaultTableProps<CourseRun> & {
  courseId?: string;
};

export function CoursesRunsList({ courseId, ...props }: Props) {
  const intl = useIntl();
  const copyToClipboard = useCopyToClipboard();
  const { push } = useRouter();

  const paginatedResource = usePaginatedTableResource<
    CourseRun,
    CourseRunResourcesQuery
  >({
    useResource: useCoursesRuns,
    changeUrlOnPageChange: props.changeUrlOnPageChange,
    filters: { courseId },
  });

  const columns: GridColDef[] = useMemo(
    () => getCoursesRunsListColumns(intl),
    [intl],
  );

  const useAsTemplate = (courseRun: CourseRun) => {
    if (courseRun.id === undefined) {
      return;
    }
    push(`${PATH_ADMIN.courses_run.create}?from=${courseRun?.id}`);
  };

  return (
    <TableComponent
      {...paginatedResource.tableProps}
      {...props}
      filters={<CourseRunFilters {...paginatedResource.filtersProps} />}
      columns={columns}
      columnBuffer={6}
      getOptions={(courseRun) => {
        const { uri, resource_link: resourceLink } = courseRun;

        if (uri === undefined) {
          return [];
        }

        return [
          {
            mainLabel: intl.formatMessage(commonTranslations.copyUrl),
            icon: <CopyAllIcon fontSize="small" />,
            onClick: () => copyToClipboard(uri),
          },
          {
            mainLabel: intl.formatMessage(messages.copyResourceLink),
            icon: <CopyAllIcon fontSize="small" />,
            onClick: () => copyToClipboard(resourceLink),
          },
        ];
      }}
      onEditClick={(courseRun: CourseRun) => {
        if (courseRun.id) {
          push(PATH_ADMIN.courses_run.edit(courseRun?.id));
        }
      }}
      onUseAsTemplateClick={useAsTemplate}
      getEntityName={(courseRun) => {
        return courseRun.title;
      }}
      onRemoveClick={(courseRun: CourseRun) => {
        paginatedResource.methods.delete(courseRun.id);
      }}
    />
  );
}
