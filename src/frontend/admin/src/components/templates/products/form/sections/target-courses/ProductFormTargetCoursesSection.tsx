import * as React from "react";
import { useState } from "react";

import { useFieldArray, useForm } from "react-hook-form";
import Grid from "@mui/material/Unstable_Grid2";
import Typography from "@mui/material/Typography";
import { useIntl } from "react-intl";
import Alert from "@mui/material/Alert";
import * as Yup from "yup";
import { yupResolver } from "@hookform/resolvers/yup";
import { DndList } from "@/components/presentational/dnd/DndList";
import { useModal } from "@/components/presentational/modal/useModal";
import { productFormMessages } from "@/components/templates/products/form/translations";
import { CustomModal } from "@/components/presentational/modal/Modal";
import { ProductTargetCourseRelationForm } from "@/components/templates/products/form/sections/target-courses/ProductTargetCourseRelationForm";
import { Maybe, ToFormValues } from "@/types/utils";
import {
  ProductTargetCourseRelation,
  ProductTargetCourseRelationFormValues,
  ProductTargetCourseRelationOptionalId,
} from "@/services/api/models/ProductTargetCourseRelation";
import { WizardStepProps } from "@/components/presentational/wizard/Wizard";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { useProducts } from "@/hooks/useProducts/useProducts";
import { transformProductTargetCourseRelationToDTO } from "@/services/api/models/Product";
import { ProductFormTargetCourseRow } from "@/components/templates/products/form/sections/target-courses/ProductFormTargetCourseRow";
import { useList } from "@/hooks/useList/useList";

type EditRelationState = {
  item: ProductTargetCourseRelation;
  arrayIndex: number;
};

export type ProductTargetCoursesFormValues = ToFormValues<{
  target_courses?: ProductTargetCourseRelation[];
}>;

type Props = WizardStepProps & {
  productId: string;
  target_courses?: ProductTargetCourseRelation[];
};

const Schema = Yup.object().shape({
  target_courses: Yup.array<ProductTargetCourseRelation>().optional(),
});

export function ProductFormTargetCoursesSection(props: Props) {
  const intl = useIntl();
  const modal = useModal();
  const products = useProducts({}, { enabled: false });
  const [editRelationState, setEditRelationState] =
    useState<Maybe<EditRelationState>>();

  const { items: creatingList, ...creatingListMethods } =
    useList<ProductTargetCourseRelationOptionalId>([]);

  const getDefaultValues = (): ProductTargetCoursesFormValues => {
    return {
      target_courses: props?.target_courses ?? [],
    };
  };

  const methods = useForm({
    resolver: yupResolver(Schema),
    defaultValues: getDefaultValues(),
  });

  const targetCourses = useFieldArray({
    control: methods.control,
    name: "target_courses",
    keyName: "arrayIdField",
  });

  const handleUpdate = (
    values: ProductTargetCourseRelationFormValues,
    arrayIndex: number,
  ): void => {
    if (arrayIndex < 0 || !editRelationState) {
      return;
    }

    const newValue: ProductTargetCourseRelation = {
      ...editRelationState.item,
      course: values!.course,
      course_runs: values.course_runs ?? [],
    };
    const payload = transformProductTargetCourseRelationToDTO(newValue);
    targetCourses.update(arrayIndex, newValue);
    products.methods.updateTargetCourse(
      {
        productId: props.productId,
        relationId: editRelationState.item.course.id,
        payload,
      },
      {
        onError: () => {
          targetCourses.update(arrayIndex, editRelationState.item);
        },
      },
    );
  };

  const handleCreate = (
    values: ProductTargetCourseRelationFormValues,
  ): void => {
    const newValue: ProductTargetCourseRelationOptionalId = {
      course: values.course,
      course_runs: values.course_runs ?? [],
      position: targetCourses.fields.length,
    };
    const payload = transformProductTargetCourseRelationToDTO(newValue);

    creatingListMethods.push(newValue);

    products.methods.addTargetCourse(
      { productId: props.productId, payload },
      {
        onSuccess: (data) => {
          targetCourses.update(targetCourses.fields.length, data);
        },
        onSettled: () => {
          creatingListMethods.clear();
        },
      },
    );
  };

  const handleRemove = (
    item: ProductTargetCourseRelation,
    index: number,
  ): void => {
    if (item.id === undefined) {
      return;
    }

    targetCourses.remove(index);
    products.methods.removeTargetCourse(
      { productId: props.productId, relationId: item.course.id },
      {
        onError: () => {
          targetCourses.insert(index, item);
        },
      },
    );
  };

  const handleReorder = (items: ProductTargetCourseRelation[]): void => {
    const targetCoursesOrder: string[] = items.map((value) => value.course.id);
    const olfFields = [...targetCourses.fields];
    targetCourses.replace(items);
    products.methods.reorderTargetCourses(
      { productId: props.productId, target_courses: targetCoursesOrder },
      {
        onError: () => {
          targetCourses.replace(olfFields);
        },
      },
    );
  };

  return (
    <RHFProvider
      id="product-target-courses-form"
      showSubmit={false}
      methods={methods}
    >
      <Grid container spacing={2}>
        <Grid xs={12}>
          <Alert severity="info">
            {intl.formatMessage(productFormMessages.targetCoursesHelperSection)}
          </Alert>
        </Grid>
        <Grid xs={12}>
          <Typography variant="subtitle2">
            {intl.formatMessage(productFormMessages.targetCoursesTitle)}
          </Typography>
        </Grid>

        <Grid xs={12}>
          <DndList<
            ProductTargetCourseRelation,
            ProductTargetCourseRelationOptionalId
          >
            creatingRows={creatingList}
            emptyLabel={intl.formatMessage(productFormMessages.noTargetCourses)}
            addButtonLabel={intl.formatMessage(
              productFormMessages.addTargetCourseButtonLabel,
            )}
            onSorted={handleReorder}
            addButtonClick={() => {
              setEditRelationState(undefined);
              modal.handleOpen();
            }}
            droppableId="course-sections"
            rows={targetCourses.fields}
            renderRow={(item, index) => {
              return (
                <ProductFormTargetCourseRow
                  item={item}
                  key={`row-${item.course.id}`}
                  onDelete={() => handleRemove(item, index)}
                  onEdit={() => {
                    setEditRelationState({ item, arrayIndex: index });
                    modal.handleOpen();
                  }}
                />
              );
            }}
            renderCreatingRow={(item) => {
              return (
                <ProductFormTargetCourseRow
                  item={item}
                  key={`creating-row-${item.course.id}`}
                />
              );
            }}
          />
        </Grid>
      </Grid>
      <CustomModal
        fullWidth={true}
        maxWidth="md"
        title={intl.formatMessage(
          productFormMessages.addTargetCourseRelationModalTitle,
        )}
        {...modal}
        handleClose={() => {
          setEditRelationState(undefined);
          modal.handleClose();
        }}
      >
        <ProductTargetCourseRelationForm
          targetCourse={editRelationState?.item}
          onSubmit={(item) => {
            if (editRelationState) {
              handleUpdate(item, editRelationState.arrayIndex);
            } else {
              handleCreate(item);
            }

            modal.handleClose();
          }}
        />
      </CustomModal>
    </RHFProvider>
  );
}
