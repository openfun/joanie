import * as React from "react";
import { useEffect } from "react";
import * as Yup from "yup";
import { lazy } from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Grid2";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useIntl } from "react-intl";
import moment from "moment";
import {
  Course,
  CourseFormValues,
  DTOCourse,
  transformCourseToDTO,
} from "@/services/api/models/Course";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { courseFormMessages } from "@/components/templates/courses/form/translations";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { OrganizationSearch } from "@/components/templates/organizations/inputs/search/OrganizationSearch";
import { ServerSideErrorForm } from "@/types/utils";
import { useCourses } from "@/hooks/useCourses/useCourses";
import { genericUpdateFormError } from "@/utils/forms";
import { TranslatableForm } from "@/components/presentational/translatable-content/TranslatableForm";
import { Organization } from "@/services/api/models/Organization";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { RHFUploadImage } from "@/components/presentational/hook-form/RHFUploadImage";
import { ThumbnailDetailField } from "@/services/api/models/Image";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { useFormSubmit } from "@/hooks/form/useFormSubmit";

interface Props {
  afterSubmit?: (course: Course) => void;
  isLoading?: boolean;
  course?: Course;
  fromCourse?: Course;
}

export function CourseGeneralForm({ course, ...props }: Props) {
  const intl = useIntl();
  const formSubmitProps = useFormSubmit(course);
  const coursesQuery = useCourses({}, { enabled: false });
  const defaultCourse = course ?? props.fromCourse;

  const getUploadedCover = (): ThumbnailDetailField[] => {
    if (!course) {
      return [];
    }
    return defaultCourse?.cover ? [defaultCourse.cover] : [];
  };

  const RegisterSchema = Yup.object().shape({
    code: Yup.string().required(),
    title: Yup.string().required(),
    organizations: Yup.array<any, Organization>().min(1).required(),
    cover: Yup.mixed(),
    effort: lazy((value) => {
      return value === ""
        ? Yup.string().nullable().optional()
        : Yup.number().min(0).nullable().optional();
    }),
  });

  const getDefaultValues = () => {
    return {
      code: defaultCourse?.code ?? "",
      title: defaultCourse?.title ?? "",
      organizations: defaultCourse?.organizations ?? [],
      cover: undefined,
      effort: defaultCourse?.effort
        ? moment.duration(defaultCourse.effort).asHours()
        : "",
    };
  };

  const methods = useForm({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues() as any,
  });

  const updateFormError = (errors: ServerSideErrorForm<CourseFormValues>) => {
    genericUpdateFormError(errors, methods.setError);
  };

  const onSubmit = (values: CourseFormValues): void => {
    const payload: DTOCourse = transformCourseToDTO(values);

    if (course) {
      payload.id = course.id;

      coursesQuery.methods.update(payload, {
        onSuccess: (updatedCourse) => {
          props.afterSubmit?.(updatedCourse);
        },
        onError: (error) => updateFormError(error.data),
      });
    } else {
      coursesQuery.methods.create(payload, {
        onSuccess: (createCourse) => props.afterSubmit?.(createCourse),
        onError: (error) => updateFormError(error.data),
      });
    }
  };

  useEffect(() => {
    methods.reset(getDefaultValues());
  }, [course]);

  return (
    <SimpleCard>
      <TranslatableForm
        entitiesDeps={[course]}
        resetForm={() => methods.reset(getDefaultValues())}
        onSelectLang={() => {
          if (course) coursesQuery.methods.invalidate();
        }}
      >
        <Box padding={4}>
          <RHFProvider
            checkBeforeUnload={true}
            showSubmit={formSubmitProps.showSubmit}
            methods={methods}
            id="course-form"
            onSubmit={methods.handleSubmit(onSubmit)}
          >
            <RHFValuesChange
              autoSave={formSubmitProps.enableAutoSave}
              onSubmit={onSubmit}
            >
              <Grid container spacing={2}>
                <Grid size={12}>
                  <Typography variant="subtitle2">
                    {intl.formatMessage(courseFormMessages.generalSubtitle)}
                  </Typography>
                </Grid>
                <Grid size={12}>
                  <RHFTextField
                    name="title"
                    label={intl.formatMessage(commonTranslations.title)}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <RHFTextField
                    name="code"
                    label={intl.formatMessage(courseFormMessages.codeLabel)}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <RHFTextField
                    type="number"
                    name="effort"
                    helperText={intl.formatMessage(
                      courseFormMessages.effortHelperText,
                    )}
                    label={intl.formatMessage(courseFormMessages.effortLabel)}
                  />
                </Grid>

                <Grid size={12}>
                  <OrganizationSearch
                    enableAdd={true}
                    multiple={true}
                    name="organizations"
                    label={intl.formatMessage(
                      courseFormMessages.organizationsLabel,
                    )}
                  />
                </Grid>
                <Grid size={12}>
                  <RHFUploadImage
                    thumbnailFiles={getUploadedCover()}
                    name="cover"
                    buttonLabel={intl.formatMessage(
                      courseFormMessages.uploadCoverButtonLabel,
                    )}
                    accept="image/*"
                    label={intl.formatMessage(courseFormMessages.coverLabel)}
                  />
                </Grid>
              </Grid>
            </RHFValuesChange>
          </RHFProvider>
        </Box>
      </TranslatableForm>
    </SimpleCard>
  );
}
