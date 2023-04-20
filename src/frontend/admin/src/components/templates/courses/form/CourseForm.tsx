import * as React from "react";
import { useEffect, useState } from "react";
import * as Yup from "yup";
import { useFieldArray, useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Unstable_Grid2";
import { Box, Button, Stack, Typography } from "@mui/material";
import { useIntl } from "react-intl";
import { useSnackbar } from "notistack";
import {
  Course,
  CourseFormValue,
  DTOCourse,
  transformCourseToDTO,
} from "@/services/api/models/Course";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { courseFormMessages } from "@/components/templates/courses/form/translations";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { useModal } from "@/components/presentational/modal/useModal";
import { CourseFormProductRelationModal } from "@/components/templates/courses/form/product-relation/CourseFormProductRelationModal";
import { CourseProductRelationFormSchema } from "@/components/templates/courses/form/product-relation/CourseProductRelationForm";
import { DndDefaultRow } from "@/components/presentational/dnd/DndDefaultRow";
import { OrganizationSearch } from "@/components/templates/organizations/inputs/search/OrganizationSearch";
import { CourseRelationToProduct } from "@/services/api/models/Relations";
import { Maybe, ServerSideErrorForm } from "@/types/utils";
import { useCourses } from "@/hooks/useCourses/useCourses";
import { genericUpdateFormError } from "@/utils/forms";
import { TranslatableContent } from "@/components/presentational/translatable-content/TranslatableContent";

interface Props {
  afterSubmit?: (course: Course) => void;
  course?: Course;
}

export function CourseForm({ course, ...props }: Props) {
  const intl = useIntl();
  const courses = useCourses({}, { enabled: false });
  const { enqueueSnackbar } = useSnackbar();

  const relationToProductModal = useModal();
  const [editRelationToProduct, setEditRelationToProduct] =
    useState<Maybe<CourseRelationToProduct>>();
  const [editRelationToProductIndex, setEditRelationToProductIndex] =
    useState<Maybe<number>>();

  const RegisterSchema = Yup.object().shape({
    code: Yup.string().required(),
    title: Yup.string().required(),
    organizations: Yup.array().min(1),
    product_relations: Yup.array().of(CourseProductRelationFormSchema),
  });

  const getDefaultValues = () => {
    return {
      code: course?.code ?? "",
      title: course?.title ?? "",
      organizations: course?.organizations ?? [],
      product_relations: course?.product_relations ?? [],
    };
  };

  const methods = useForm<CourseFormValue>({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues(),
  });

  const productsArray = useFieldArray({
    control: methods.control,
    name: "product_relations",
  });

  const editRelation = (
    relation: CourseRelationToProduct,
    index: number
  ): void => {
    setEditRelationToProduct(relation);
    setEditRelationToProductIndex(index);
    relationToProductModal.handleOpen();
  };

  const updateFormError = (errors: ServerSideErrorForm<CourseFormValue>) => {
    genericUpdateFormError(errors, methods.setError);
  };

  const onSubmit = (values: CourseFormValue): void => {
    const payload: DTOCourse = transformCourseToDTO(values);

    if (course) {
      payload.id = course.id;

      courses.methods.update(payload, {
        onSuccess: (updatedCourse) => {
          props.afterSubmit?.(updatedCourse);
          enqueueSnackbar("Success", { variant: "success" });
        },
        onError: (error) => updateFormError(error.data),
      });
    } else {
      courses.methods.create(payload, {
        onSuccess: (createCourse) => props.afterSubmit?.(createCourse),
        onError: (error) => updateFormError(error.data),
      });
    }
  };

  useEffect(() => {
    methods.reset(getDefaultValues());
  }, [course]);

  return (
    <TranslatableContent
      onSelectLang={() => {
        if (course) courses.methods.invalidate();
      }}
    >
      <Box padding={4}>
        <RHFProvider
          methods={methods}
          id="course-form"
          onSubmit={methods.handleSubmit(onSubmit)}
        >
          <Grid container spacing={2}>
            <Grid xs={12}>
              <Typography variant="subtitle2">
                {intl.formatMessage(courseFormMessages.generalSubtitle)}
              </Typography>
            </Grid>
            <Grid xs={12} md={6}>
              <RHFTextField
                name="title"
                label={intl.formatMessage(commonTranslations.title)}
              />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFTextField
                name="code"
                label={intl.formatMessage(courseFormMessages.codeLabel)}
              />
            </Grid>

            <Grid xs={12}>
              <OrganizationSearch
                multiple={true}
                name="organizations"
                label={intl.formatMessage(
                  courseFormMessages.organizationsLabel
                )}
              />
            </Grid>

            <Grid xs={12} md={6}>
              <Typography variant="subtitle2">
                {intl.formatMessage(courseFormMessages.productRelationSubtitle)}
              </Typography>
            </Grid>
            <Grid xs={12} md={6}>
              <Box display="flex" width="100%" justifyContent="flex-end">
                <Button
                  size="small"
                  onClick={relationToProductModal.handleOpen}
                >
                  {intl.formatMessage(
                    courseFormMessages.addRelationButtonLabel
                  )}
                </Button>
              </Box>
            </Grid>
            <Grid xs={12}>
              <Stack spacing={1}>
                {productsArray.fields.map((product, index) => (
                  <DndDefaultRow
                    key={`${product.product.title}-${index}`}
                    onDelete={() => productsArray.remove(index)}
                    mainTitle={product.product.title}
                    rightActions={
                      <Button onClick={() => editRelation(product, index)}>
                        Edit
                      </Button>
                    }
                    subTitle={`${product.organizations.length} organizations selectionnées`}
                  />
                ))}
              </Stack>
            </Grid>
          </Grid>
        </RHFProvider>
        <CourseFormProductRelationModal
          onAdd={(relation) => {
            productsArray.append(relation);
            relationToProductModal.handleClose();
          }}
          onEdit={(relation) => {
            if (
              editRelationToProductIndex !== undefined &&
              editRelationToProductIndex >= 0
            ) {
              productsArray.update(editRelationToProductIndex, relation);
            }
            relationToProductModal.handleClose();
          }}
          open={relationToProductModal.open}
          courseRelationToProduct={editRelationToProduct}
          handleClose={() => {
            setEditRelationToProductIndex(undefined);
            setEditRelationToProduct(undefined);
            relationToProductModal.handleClose();
          }}
        />
      </Box>
    </TranslatableContent>
  );
}
