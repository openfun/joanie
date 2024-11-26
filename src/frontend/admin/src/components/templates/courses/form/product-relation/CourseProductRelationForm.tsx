import * as React from "react";
import * as Yup from "yup";
import { useFieldArray, useForm } from "react-hook-form";
import Grid from "@mui/material/Grid2";
import { yupResolver } from "@hookform/resolvers/yup";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { defineMessages, FormattedMessage, useIntl } from "react-intl";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { DTOCourseProductRelation } from "@/services/api/models/Relations";
import { Organization } from "@/services/api/models/Organization";
import { DndDefaultRow } from "@/components/presentational/dnd/DndDefaultRow";
import { ProductSearch } from "@/components/templates/products/inputs/search/ProductSearch";
import { OrganizationControlledSearch } from "@/components/templates/organizations/inputs/search/OrganizationControlledSearch";
import { BaseProduct, Product } from "@/services/api/models/Product";
import { Course } from "@/services/api/models/Course";
import { CourseSearch } from "@/components/templates/courses/inputs/search/CourseSearch";

const messages = defineMessages({
  productLabel: {
    id: "components.templates.course.form.translations.productRelation.productLabel",
    defaultMessage: "Product",
    description: "Product label for the CourseProductRelation form",
  },
  courseLabel: {
    id: "components.templates.course.form.translations.productRelation.courseLabel",
    defaultMessage: "Course",
    description: "Course label for the CourseProductRelation form",
  },
  chooseProduct: {
    id: "components.templates.course.form.translations.productRelation.chooseProduct",
    defaultMessage: "Choose your product",
    description: "Label form the product search input",
  },
  chooseCourse: {
    id: "components.templates.course.form.translations.productRelation.chooseCourse",
    defaultMessage: "Choose your course",
    description: "Label form the course search input",
  },
  organizationsTitle: {
    id: "components.templates.course.form.translations.productRelation.organizationsTitle",
    defaultMessage: "Managed by this organizations",
    description: "Title for the organizations section",
  },
});

export interface CourseProductRelationFormValues {
  product: Product | null;
  course: Course | null;
  organizations: Organization[];
}

interface BaseProps {
  onSubmit?: (
    payload: DTOCourseProductRelation,
    formValues: CourseProductRelationFormValues,
  ) => void;
  defaultProduct?: BaseProduct;
  defaultCourse?: Course;
  organizations?: Organization[];
  courseId?: string;
  productId?: string;
}

type Props = BaseProps;

export const CourseProductRelationFormSchema = Yup.object().shape({
  product: Yup.mixed<Product>().required().nullable(),
  course: Yup.mixed<Course>().required().nullable(),
  organizations: Yup.array().required(),
});

export function CourseProductRelationForm({
  defaultProduct,
  defaultCourse,
  organizations,
  onSubmit,
  productId,
  courseId,
}: Props) {
  const intl = useIntl();

  const methods = useForm<CourseProductRelationFormValues>({
    resolver: yupResolver(CourseProductRelationFormSchema) as any,
    defaultValues: {
      product: defaultProduct ?? null,
      course: defaultCourse ?? null,
      organizations: organizations ?? [],
    },
  });

  const organizationArray = useFieldArray({
    control: methods.control,
    name: "organizations",
  });

  return (
    <RHFProvider
      methods={methods}
      id="course-relation-to-products-form"
      onSubmit={methods.handleSubmit((values) => {
        let payload: DTOCourseProductRelation;

        if (courseId) {
          payload = {
            product_id: values.product!.id,
            course_id: courseId,
            organization_ids: values.organizations.map((org) => org.id),
          };
        } else if (productId) {
          payload = {
            product_id: productId,
            course_id: values.course!.id,
            organization_ids: values.organizations.map((org) => org.id),
          };
        }
        onSubmit?.(payload!, values);
      })}
    >
      <Grid container spacing={2}>
        <Grid size={12}>
          <Typography variant="subtitle2">
            <FormattedMessage
              {...(productId ? messages.courseLabel : messages.productLabel)}
            />
          </Typography>
        </Grid>
        <Grid size={12}>
          {courseId && (
            <ProductSearch
              name="product"
              label={intl.formatMessage(messages.chooseProduct)}
            />
          )}
          {productId && (
            <CourseSearch
              name="course"
              label={intl.formatMessage(messages.chooseCourse)}
            />
          )}
        </Grid>
        <Grid size={12}>
          <Typography variant="subtitle2">
            <FormattedMessage {...messages.organizationsTitle} />
          </Typography>
        </Grid>
        <Grid size={12}>
          <OrganizationControlledSearch
            onSelectItem={(item) => {
              organizationArray.append(item);
            }}
          />
        </Grid>
        <Grid size={12}>
          <Stack spacing={1}>
            {organizationArray.fields.map((org, index) => (
              <DndDefaultRow
                key={org.id}
                onDelete={() => organizationArray.remove(index)}
                mainTitle={org.title}
              />
            ))}
          </Stack>
        </Grid>
      </Grid>
    </RHFProvider>
  );
}
