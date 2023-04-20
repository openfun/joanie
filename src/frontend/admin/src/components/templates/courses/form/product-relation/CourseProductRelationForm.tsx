import * as React from "react";
import * as Yup from "yup";
import { useFieldArray, useForm } from "react-hook-form";

import Grid from "@mui/material/Unstable_Grid2";
import { yupResolver } from "@hookform/resolvers/yup";
import { Stack, Typography } from "@mui/material";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { CourseRelationToProduct } from "@/services/api/models/Relations";
import { Organization } from "@/services/api/models/Organization";
import { DndDefaultRow } from "@/components/presentational/dnd/DndDefaultRow";
import { ProductSearch } from "@/components/templates/products/inputs/search/ProductSearch";
import { OrganizationControlledSearch } from "@/components/templates/organizations/inputs/search/OrganizationControlledSearch";
import { Product } from "@/services/api/models/Product";

interface FormValues {
  product?: Product | null;
  organizations: Organization[];
}

interface Props {
  onSubmit?: (relation: CourseRelationToProduct) => void;
  relation?: CourseRelationToProduct;
}

export const CourseProductRelationFormSchema = Yup.object().shape({
  product: Yup.mixed().required(),
  organizations: Yup.array().of(Yup.mixed()).min(1),
});

export function CourseProductRelationForm({ relation, onSubmit }: Props) {
  const methods = useForm<FormValues>({
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
        onSubmit?.(values as CourseRelationToProduct);
      })}
    >
      <Grid container spacing={2}>
        <Grid xs={12}>
          <Typography variant="subtitle2">Product</Typography>
        </Grid>
        <Grid xs={12}>
          <ProductSearch name="product" label="Choose your product" />
        </Grid>
        <Grid xs={12}>
          <Typography variant="subtitle2">
            Managed by this organizations
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
