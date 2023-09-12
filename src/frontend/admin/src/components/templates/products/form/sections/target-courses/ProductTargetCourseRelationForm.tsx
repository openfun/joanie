import * as React from "react";
import { useEffect } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import * as Yup from "yup";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Unstable_Grid2";
import Stack from "@mui/material/Stack";
import { useIntl } from "react-intl";
import Alert from "@mui/material/Alert";
import {
  ProductTargetCourseRelation,
  ProductTargetCourseRelationFormValues,
} from "@/services/api/models/ProductTargetCourseRelation";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { CourseSearch } from "@/components/templates/courses/inputs/search/CourseSearch";
import { DndDefaultRow } from "@/components/presentational/dnd/DndDefaultRow";
import { CourseRunControlledSearch } from "@/components/templates/courses-runs/input/search/CourseRunControlledSearch";
import { CourseRun } from "@/services/api/models/CourseRun";
import { productFormMessages } from "@/components/templates/products/form/translations";
import { Course } from "@/services/api/models/Course";
import { Optional } from "@/types/utils";
import { RHFCheckbox } from "@/components/presentational/hook-form/RHFCheckbox";

type Props = {
  targetCourse?: Optional<ProductTargetCourseRelation, "id">;
  onSubmit: (target: ProductTargetCourseRelationFormValues) => void;
};
export function ProductTargetCourseRelationForm(props: Props) {
  const intl = useIntl();

  const Schema = Yup.object().shape({
    course: Yup.mixed<Course>().required(),
    course_runs: Yup.array<CourseRun>().min(0).optional(),
    enable_course_runs: Yup.boolean().optional(),
  });

  const getDefaultValues = (): ProductTargetCourseRelationFormValues => {
    let courseRunsDefault: CourseRun[] = [];
    let courseDefault: any = null;
    if (props.targetCourse) {
      const { course_runs: courseRuns, ...course } = props.targetCourse;
      courseRunsDefault = courseRuns ?? [];
      courseDefault = course.course;
    }
    let enableCourseRuns = false;
    if (props?.targetCourse?.course_runs) {
      enableCourseRuns = props.targetCourse.course_runs.length > 0;
    }

    return {
      course: courseDefault,
      course_runs: courseRunsDefault,
      enable_course_runs: enableCourseRuns,
    };
  };

  const form = useForm<ProductTargetCourseRelationFormValues>({
    resolver: yupResolver(Schema),
    defaultValues: getDefaultValues(),
  });

  const onSubmit = (values: ProductTargetCourseRelationFormValues): void => {
    props.onSubmit({
      course: values.course,
      course_runs: values.course_runs ?? [],
      enable_course_runs: undefined,
    });
  };

  const courseRunsArray = useFieldArray({
    control: form.control,
    name: "course_runs",
  });

  const valueCourse = form.watch("course", undefined);
  const useSpecificCourseRuns = form.watch("enable_course_runs", false);

  useEffect(() => {
    form.reset(getDefaultValues());
  }, [props.targetCourse]);

  return (
    <RHFProvider
      id="product-target-course-form"
      methods={form}
      onSubmit={form.handleSubmit(onSubmit)}
    >
      <Grid container>
        <Grid xs={12}>
          <Alert severity="info">
            {intl.formatMessage(
              productFormMessages.productTargetCourseFormInfo,
            )}
          </Alert>
        </Grid>
        <Grid xs={12} mt={2}>
          <Stack spacing={2}>
            <CourseSearch name="course" />
            {valueCourse != null && (
              <>
                <RHFCheckbox
                  name="enable_course_runs"
                  label={intl.formatMessage(
                    productFormMessages.useSpecificCourseRunsCheckboxLabel,
                  )}
                />
                {/* <FormControlLabel */}
                {/*  control={ */}
                {/*    <Checkbox */}
                {/*      onChange={(event: ChangeEvent<HTMLInputElement>) => { */}
                {/*        const { checked } = event.target; */}
                {/*        if (!checked) { */}
                {/*          courseRunsArray.replace([]); */}
                {/*        } */}
                {/*        setUseSpecificCourseRuns(checked); */}
                {/*      }} */}
                {/*      checked={useSpecificCourseRuns} */}
                {/*    /> */}
                {/*  } */}
                {/*  label={intl.formatMessage( */}
                {/*    productFormMessages.useSpecificCourseRunsCheckboxLabel, */}
                {/*  )} */}
                {/* /> */}
                {useSpecificCourseRuns && (
                  <>
                    <CourseRunControlledSearch
                      courseId={valueCourse.id}
                      selectedOptions={courseRunsArray.fields}
                      onSelectItem={(item) => {
                        courseRunsArray.append(item);
                      }}
                    />
                    <Stack spacing={1}>
                      {courseRunsArray.fields.map((courseRun, index) => {
                        return (
                          <DndDefaultRow
                            key={courseRun.id}
                            mainTitle={courseRun.title}
                            onDelete={() => courseRunsArray.remove(index)}
                          />
                        );
                      })}
                    </Stack>
                  </>
                )}
              </>
            )}
          </Stack>
        </Grid>
      </Grid>
    </RHFProvider>
  );
}
