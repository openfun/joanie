import * as React from "react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import * as Yup from "yup";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Unstable_Grid2";
import Stack from "@mui/material/Stack";
import { FormattedMessage, useIntl } from "react-intl";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Switch from "@mui/material/Switch";
import {
  DEFAULT_IS_GRADED_VALUE,
  ProductTargetCourseRelation,
  ProductTargetCourseRelationFormValues,
} from "@/services/api/models/ProductTargetCourseRelation";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { CourseSearch } from "@/components/templates/courses/inputs/search/CourseSearch";
import { productFormMessages } from "@/components/templates/products/form/translations";
import { Optional } from "@/types/utils";
import { CoursesRunsList } from "@/components/templates/courses-runs/list/CoursesRunsList";
import { Course } from "@/services/api/models/Course";
import { CourseRun } from "@/services/api/models/CourseRun";
import RHFSwitch from "@/components/presentational/hook-form/RHFSwitch";

type Props = {
  targetCourse?: Optional<ProductTargetCourseRelation, "id">;
  onSubmit: (target: ProductTargetCourseRelationFormValues) => void;
};
export function ProductTargetCourseRelationForm(props: Props) {
  const intl = useIntl();
  const [enableCourseRuns, setEnableCourseRuns] = useState(
    props.targetCourse && props.targetCourse.course_runs
      ? props.targetCourse.course_runs.length > 0
      : false,
  );

  const Schema = Yup.object().shape({
    course: Yup.mixed<Course>().required(),
    is_graded: Yup.boolean().required(),
    course_runs: Yup.array<any, CourseRun>().min(0).optional(),
  });

  const getDefaultValues = (): ProductTargetCourseRelationFormValues => {
    let courseRunsDefault: CourseRun[] = [];
    let courseDefault: any = null;

    if (props.targetCourse) {
      const { course_runs: courseRuns, ...course } = props.targetCourse;
      courseRunsDefault = courseRuns ?? [];
      courseDefault = course.course;
    }

    return {
      course: courseDefault,
      course_runs: courseRunsDefault,
      is_graded: props.targetCourse?.is_graded ?? DEFAULT_IS_GRADED_VALUE,
    };
  };

  const methods = useForm({
    resolver: yupResolver(Schema),
    defaultValues: getDefaultValues(),
  });

  const onSubmit = (values: ProductTargetCourseRelationFormValues): void => {
    props.onSubmit({
      course: values.course,
      course_runs: values.course_runs ?? [],
      is_graded: values.is_graded ?? DEFAULT_IS_GRADED_VALUE,
    });
  };

  const valueCourse = methods.watch("course");
  const courseRuns = methods.watch("course_runs");

  useEffect(() => {
    if (!valueCourse) {
      setEnableCourseRuns(false);
    }
  }, [valueCourse]);

  useEffect(() => {
    methods.reset(getDefaultValues());
  }, [props.targetCourse]);

  return (
    <RHFProvider
      id="product-target-course-form"
      methods={methods}
      onSubmit={methods.handleSubmit(onSubmit)}
    >
      <Grid container spacing={2}>
        <Grid xs={12}>
          <Alert severity="info">
            {intl.formatMessage(
              productFormMessages.productTargetCourseFormInfo,
            )}
          </Alert>
        </Grid>
        <Grid xs={12} mt={3}>
          <Stack spacing={2}>
            <CourseSearch enableAdd enableEdit name="course" />
            <RHFSwitch
              name="is_graded"
              label={intl.formatMessage(
                productFormMessages.targetCourseIsGradedLabel,
              )}
            />

            {valueCourse != null && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle2" component="h6">
                  <FormattedMessage
                    {...productFormMessages.choiceTargetCourseCourseRunModalTitle}
                  />
                </Typography>
                <Alert
                  data-testid="product-target-course-runs-selection-alert"
                  sx={{ mt: 1 }}
                  icon={
                    <Switch
                      data-testid="enable-course-runs-selection"
                      checked={enableCourseRuns}
                      size="small"
                      onChange={(event, checked) => {
                        setEnableCourseRuns(checked);
                        if (!checked) {
                          methods.setValue("course_runs", []);
                        }
                      }}
                    />
                  }
                  severity="warning"
                >
                  <FormattedMessage
                    {...productFormMessages.choiceTargetCourseCourseRunModalAlertContent}
                  />
                </Alert>
              </Box>
            )}

            {valueCourse != null && enableCourseRuns && (
              <Box mt={4}>
                <CoursesRunsList
                  enableDelete={false}
                  defaultSelectedRows={
                    courseRuns?.map((courseRun) => courseRun.id) ?? []
                  }
                  enableSelect
                  onSelectRows={(ids, selectedCourseRuns) => {
                    methods.setValue("course_runs", selectedCourseRuns);
                  }}
                  courseId={valueCourse.id}
                />
              </Box>
            )}
          </Stack>
        </Grid>
      </Grid>
    </RHFProvider>
  );
}
