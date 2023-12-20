import * as React from "react";
import * as Yup from "yup";
import { useFieldArray, useForm } from "react-hook-form";
import Grid from "@mui/material/Unstable_Grid2";
import { yupResolver } from "@hookform/resolvers/yup";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { defineMessages, FormattedMessage, useIntl } from "react-intl";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import {
  CourseRelationToProduct,
  DTOCourseRelationToProduct,
} from "@/services/api/models/Relations";
import { Organization } from "@/services/api/models/Organization";
import { DndDefaultRow } from "@/components/presentational/dnd/DndDefaultRow";
import { ProductSearch } from "@/components/templates/products/inputs/search/ProductSearch";
import { OrganizationControlledSearch } from "@/components/templates/organizations/inputs/search/OrganizationControlledSearch";
import { Product } from "@/services/api/models/Product";

const messages = defineMessages({
  productLabel: {
    id: "components.templates.course.form.translations.productRelation.productLabel",
    defaultMessage: "Product",
    description: "Product label for the CourseProductRelation form",
  },
  chooseProduct: {
    id: "components.templates.course.form.translations.productRelation.chooseProduct",
    defaultMessage: "Choose your product",
    description: "Label form the product search input",
  },
  organizationsTitle: {
    id: "components.templates.course.form.translations.productRelation.organizationsTitle",
    defaultMessage: "Managed by this organizations",
    description: "Title for the organizations section",
  },
});

export interface CourseProductRelationFormValues {
  product: Product | null;
  organizations: Organization[];
}

interface Props {
  courseId: string;
  onSubmit?: (
    payload: DTOCourseRelationToProduct,
    formValues: CourseProductRelationFormValues,
  ) => void;
  relation?: CourseRelationToProduct;
}

export const CourseProductRelationFormSchema = Yup.object().shape({
  product: Yup.mixed<Product>().required().nullable(),
  organizations: Yup.array().required(),
});

export function CourseProductRelationForm({
  relation,
  onSubmit,
  courseId,
}: Props) {
  const intl = useIntl();

  const methods = useForm<CourseProductRelationFormValues>({
    resolver: yupResolver(CourseProductRelationFormSchema),
    defaultValues: {
      product: relation?.product ?? null,
      organizations: relation?.organizations ?? [],
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
        const payload: DTOCourseRelationToProduct = {
          product_id: values.product!.id,
          course_id: courseId,
          organization_ids: values.organizations.map((org) => org.id),
        };
        onSubmit?.(payload, values);
      })}
    >
      <Grid container spacing={2}>
        <Grid xs={12}>
          <Typography variant="subtitle2">
            <FormattedMessage {...messages.productLabel} />
          </Typography>
        </Grid>
        <Grid xs={12}>
          <ProductSearch
            name="product"
            label={intl.formatMessage(messages.chooseProduct)}
          />
        </Grid>
        <Grid xs={12}>
          <Typography variant="subtitle2">
            <FormattedMessage {...messages.organizationsTitle} />
          </Typography>
        </Grid>
        <Grid xs={12}>
          <OrganizationControlledSearch
            onSelectItem={(item) => {
              organizationArray.append(item);
            }}
          />
        </Grid>
        <Grid xs={12}>
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
