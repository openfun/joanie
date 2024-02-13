import * as React from "react";
import { useMemo } from "react";
import { useIntl } from "react-intl";
import { useRouter } from "next/router";
import { GridColDef } from "@mui/x-data-grid";
import { useSnackbar } from "notistack";
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

type Props = DefaultTableProps<CourseRun> & {
  courseId?: string;
};

export function CoursesRunsList({ courseId, ...props }: Props) {
  const intl = useIntl();
  const snackbar = useSnackbar();
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
    () => getCoursesRunsListColumns(intl, snackbar),
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
        const { uri } = courseRun;

        if (uri === undefined) {
          return [];
        }

        return [
          {
            title: intl.formatMessage(commonTranslations.copyUrl),
            icon: <CopyAllIcon fontSize="small" />,
            onClick: () => copyToClipboard(uri),
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
