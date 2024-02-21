import * as React from "react";
import { useEffect } from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Unstable_Grid2";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useIntl } from "react-intl";
import { CourseRun, DTOCourseRun } from "@/services/api/models/CourseRun";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { RHFDateTimePicker } from "@/components/presentational/hook-form/RHFDateTimePicker";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { courseRunFormMessages } from "@/components/templates/courses-runs/form/translations";
import { CourseSearch } from "@/components/templates/courses/inputs/search/CourseSearch";
import { Course } from "@/services/api/models/Course";
import { useCoursesRuns } from "@/hooks/useCourseRun/useCourseRun";
import { ServerSideErrorForm, ToFormValues } from "@/types/utils";
import {
  JoanieLanguage,
  RHFSelectLanguage,
  useSelectLanguageUtils,
} from "@/components/presentational/hook-form/RHFSelectLanguage";
import { genericUpdateFormError } from "@/utils/forms";
import { TranslatableContent } from "@/components/presentational/translatable-content/TranslatableContent";
import { RHFCheckbox } from "@/components/presentational/hook-form/RHFCheckbox";

interface FormValues
  extends ToFormValues<
    Omit<CourseRun, "course" | "state" | "languages" | "id" | "uri">
  > {
  course: Course;
  languages: JoanieLanguage[];
}

interface Props {
  afterSubmit?: (courseRun: CourseRun) => void;
  courseRun?: CourseRun;
  fromCourseRun?: CourseRun;
  addToCourse?: Course;
}

export function CourseRunForm({ courseRun, addToCourse, ...props }: Props) {
  const intl = useIntl();
  const disableCourseInput = !!addToCourse;

  const selectLanguageUtils = useSelectLanguageUtils();
  const courseRunsQuery = useCoursesRuns({}, { enabled: false });
  const defaultCourseRun = courseRun ?? props.fromCourseRun;

  const RegisterSchema = Yup.object().shape({
    title: Yup.string().required(),
    course: Yup.object<Course>().required(),
    resource_link: Yup.string().required(),
    start: Yup.string().defined().nullable(),
    end: Yup.string().defined().nullable(),
    enrollment_start: Yup.string().defined().nullable(),
    enrollment_end: Yup.string().defined().nullable(),
    languages: Yup.array<JoanieLanguage>().required(),
    is_gradable: Yup.boolean().required(),
    is_listed: Yup.boolean().required(),
  });

  const getDefaultValues = () => {
    return {
      title: defaultCourseRun?.title ?? "",
      course: defaultCourseRun?.course ?? addToCourse ?? (null as any), // to not trigger type validation for the default values
      resource_link: defaultCourseRun?.resource_link ?? "",
      start: defaultCourseRun?.start ?? null,
      end: defaultCourseRun?.end ?? null,
      enrollment_start: defaultCourseRun?.enrollment_start ?? null,
      enrollment_end: defaultCourseRun?.enrollment_end ?? null,
      languages: selectLanguageUtils.getObjectsFromValues(
        defaultCourseRun?.languages,
      ),
      is_gradable: defaultCourseRun?.is_gradable ?? false,
      is_listed: defaultCourseRun?.is_listed ?? false,
    };
  };

  const methods = useForm({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues(),
  });

  const updateFormError = (errors: ServerSideErrorForm<FormValues>) => {
    genericUpdateFormError(errors, methods.setError);
  };

  useEffect(() => {
    methods.reset(getDefaultValues());
  }, [courseRun]);

  const onSubmit = (values: FormValues) => {
    const payload: DTOCourseRun = {
      ...values,
      course_id: values.course.id,
      languages: selectLanguageUtils.getValuesFromObjects(values.languages),
    };

    if (courseRun) {
      payload.id = courseRun.id;
      courseRunsQuery.methods.update(payload, {
        onSuccess: (data) => props.afterSubmit?.(data),
        onError: (error) => updateFormError(error.data),
      });
    } else {
      courseRunsQuery.methods.create(payload, {
        onSuccess: (data) => props.afterSubmit?.(data),
        onError: (error) => {
          updateFormError(error.data);
        },
      });
    }
  };

  return (
    <TranslatableContent
      onSelectLang={() => {
        if (courseRun) courseRunsQuery.methods.invalidate();
      }}
    >
      <Box padding={4}>
        <RHFProvider
          checkBeforeUnload={true}
          methods={methods}
          isSubmitting={
            courseRunsQuery.states.creating || courseRunsQuery.states.updating
          }
          id="course-run-form"
          onSubmit={methods.handleSubmit(onSubmit)}
        >
          <Grid container spacing={2}>
            <Grid xs={12}>
              <Typography variant="subtitle2">
                {intl.formatMessage(courseRunFormMessages.generalSubtitle)}
              </Typography>
            </Grid>
            <Grid xs={12} md={6}>
              <CourseSearch
                disabled={disableCourseInput}
                enableAdd={!disableCourseInput}
                enableEdit={!disableCourseInput}
                name="course"
                label={intl.formatMessage(courseRunFormMessages.courseLabel)}
              />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFTextField
                name="title"
                label={intl.formatMessage(commonTranslations.title)}
              />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFTextField
                name="resource_link"
                label={intl.formatMessage(
                  courseRunFormMessages.resourceLinkLabel,
                )}
              />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFSelectLanguage
                multiple={true}
                name="languages"
                label={intl.formatMessage(courseRunFormMessages.language)}
              />
            </Grid>
            <Grid xs={12}>
              <Typography variant="subtitle2">
                {intl.formatMessage(
                  courseRunFormMessages.courseRunDatesSubtitle,
                )}
              </Typography>
            </Grid>
            <Grid xs={12} md={6}>
              <RHFDateTimePicker
                name="start"
                label={intl.formatMessage(courseRunFormMessages.startLabel)}
              />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFDateTimePicker
                name="end"
                label={intl.formatMessage(courseRunFormMessages.endLabel)}
              />
            </Grid>
            <Grid xs={12}>
              <Typography variant="subtitle2">
                {intl.formatMessage(
                  courseRunFormMessages.enrollmentDatesSubtitle,
                )}
              </Typography>
            </Grid>
            <Grid xs={12} md={6}>
              <RHFDateTimePicker
                name="enrollment_start"
                label={intl.formatMessage(
                  courseRunFormMessages.enrollmentStartLabel,
                )}
              />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFDateTimePicker
                name="enrollment_end"
                label={intl.formatMessage(
                  courseRunFormMessages.enrollmentEndLabel,
                )}
              />
            </Grid>
            <Grid xs={12} sm={6}>
              <RHFCheckbox
                name="is_gradable"
                label={intl.formatMessage(
                  courseRunFormMessages.isGradableLabel,
                )}
                helperText={intl.formatMessage(
                  courseRunFormMessages.isGradableHelpText,
                )}
              />
            </Grid>
            <Grid xs={12} sm={6}>
              <RHFCheckbox
                name="is_listed"
                label={intl.formatMessage(courseRunFormMessages.isListedLabel)}
                helperText={intl.formatMessage(
                  courseRunFormMessages.isListedHelpText,
                )}
              />
            </Grid>
          </Grid>
        </RHFProvider>
      </Box>
    </TranslatableContent>
  );
}
