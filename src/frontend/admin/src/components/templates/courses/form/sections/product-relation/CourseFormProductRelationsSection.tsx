import * as React from "react";
import { useEffect, useState } from "react";
import { defineMessages, useIntl } from "react-intl";
import Stack from "@mui/material/Stack";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { Course } from "@/services/api/models/Course";
import { useModal } from "@/components/presentational/modal/useModal";
import { CourseFormProductRelationModal } from "@/components/templates/courses/form/product-relation/CourseFormProductRelationModal";
import { courseFormMessages } from "@/components/templates/courses/form/translations";
import { CourseProductRelationRow } from "@/components/templates/courses/form/sections/product-relation/CourseProductRelationRow";
import { Maybe } from "@/types/utils";
import {
  CourseRelationToProduct,
  CourseRelationToProductDummy,
  DTOCourseRelationToProduct,
} from "@/services/api/models/Relations";
import { useCourseProductRelations } from "@/hooks/useCourseProductRelation/useCourseProductRelation";
import { useList } from "@/hooks/useList/useList";
import { CourseProductRelationFormValues } from "@/components/templates/courses/form/product-relation/CourseProductRelationForm";
import { CourseProductRelationDummyRow } from "@/components/templates/courses/form/sections/product-relation/CourseProductRelationDummyRow";
import { AlertModal } from "@/components/presentational/modal/AlertModal";
import { CustomList } from "@/components/presentational/list/CustomList";

const messages = defineMessages({
  sectionHelp: {
    id: "components.templates.courses.form.productRelation.CourseFormProductRelationsSection.sectionHelp",
    description: "Help text to explain what this section is about",
    defaultMessage:
      "In this section, you can choose the products that will be displayed on this course.",
  },
  deleteRelationModalTitle: {
    id: "components.templates.courses.form.productRelation.CourseFormProductRelationsSection.deleteRelationModalTitle",
    description: "Title for the delete relation modal",
    defaultMessage: "Delete product relationship",
  },
  deleteRelationModalContent: {
    id: "components.templates.courses.form.productRelation.CourseFormProductRelationsSection.deleteRelationModalContent",
    description: "Content for the delete relation modal",
    defaultMessage: "Are you sure you want to delete this relation?",
  },
  emptyList: {
    id: "components.templates.courses.form.productRelation.CourseFormProductRelationsSection.emptyList",
    description: "Message for empty list",
    defaultMessage:
      "No product relationships have been created for this course",
  },
});

type EditRelationState = {
  relation: CourseRelationToProduct;
  index: number;
};

type Props = {
  course: Course;
  invalidateCourse: () => void;
};

export function CourseFormProductRelationsSection({
  course,
  invalidateCourse,
}: Props) {
  const intl = useIntl();
  const relationToProductModal = useModal();
  const deleteRelationModal = useModal();
  const [relationToEdit, setRelationToEdit] =
    useState<Maybe<EditRelationState>>();

  const courseProductRelationQuery = useCourseProductRelations(
    {},
    { enabled: false },
  );
  const courseProductRelationsList = useList(course.product_relations ?? []);
  const courseProductRelationsCreatingList =
    useList<CourseRelationToProductDummy>([]);

  const handleCreate = (
    payload: DTOCourseRelationToProduct,
    formValues: CourseProductRelationFormValues,
  ) => {
    const dummy: CourseRelationToProductDummy = {
      ...formValues,
      product: formValues.product!,
      can_edit: false,
      order_groups: [],
      dummyId: courseProductRelationsList.items.length + 1 + "",
    };

    relationToProductModal.handleClose();
    courseProductRelationsCreatingList.push(dummy);
    courseProductRelationQuery.methods.create(payload, {
      onSuccess: (data) => {
        courseProductRelationsList.push(data);
      },
      onSettled: () => {
        courseProductRelationsCreatingList.clear();
      },
    });
  };

  const handleEdit = (
    relationId: string,
    payload: DTOCourseRelationToProduct,
    formValues: CourseProductRelationFormValues,
  ) => {
    if (!relationToEdit) {
      return;
    }

    const dummy: CourseRelationToProduct = {
      ...relationToEdit?.relation,
      ...formValues,
      product: formValues.product!,
    };

    relationToProductModal.handleClose();
    courseProductRelationsList.updateAt(relationToEdit?.index, dummy);
    courseProductRelationQuery.methods.update(
      { id: relationId, ...payload },
      {
        onSuccess: (data) => {
          courseProductRelationsList.updateAt(relationToEdit?.index, data);
          setRelationToEdit(undefined);
          invalidateCourse();
        },
        onSettled: () => {
          courseProductRelationsCreatingList.clear();
        },
        onError: () => {
          courseProductRelationsList.updateAt(
            relationToEdit?.index,
            relationToEdit.relation,
          );
        },
      },
    );
  };

  const handleDelete = () => {
    if (!relationToEdit) {
      return;
    }

    const relationId = relationToEdit.relation.id;

    relationToProductModal.handleClose();
    courseProductRelationsList.removeAt(relationToEdit?.index);
    courseProductRelationQuery.methods.delete(relationId, {
      onSuccess: () => {
        setRelationToEdit(undefined);
        invalidateCourse();
      },
      onError: () => {
        courseProductRelationsList.insertAt(
          relationToEdit?.index,
          relationToEdit.relation,
        );
      },
    });
  };

  useEffect(() => {
    courseProductRelationsList.set(course.product_relations ?? []);
  }, [course]);

  return (
    <>
      <SimpleCard>
        <Box padding={3}>
          <Stack padding={3} gap={2}>
            <Alert severity="info">
              {intl.formatMessage(messages.sectionHelp)}
            </Alert>
            <Box
              sx={{
                display: "flex",
                flexDirection: { xs: "column", md: "row" },
                justifyContent: { xs: "flex-start", md: "space-between" },
                alignItems: { xs: "flex-start", md: "center" },
              }}
            >
              <Typography variant="h6">
                {intl.formatMessage(courseFormMessages.productRelationSubtitle)}
              </Typography>
              <Button
                size="small"
                variant="contained"
                sx={{ mt: { xs: 1 } }}
                onClick={relationToProductModal.handleOpen}
              >
                {intl.formatMessage(courseFormMessages.addRelationButtonLabel)}
              </Button>
            </Box>
          </Stack>
          <CustomList
            emptyListMessage={intl.formatMessage(messages.emptyList)}
            rows={courseProductRelationsList.items}
            dummyRows={courseProductRelationsCreatingList.items}
            renderRow={(relation, index) => (
              <CourseProductRelationRow
                key={relation.id}
                invalidateCourse={invalidateCourse}
                relation={relation}
                onClickDelete={() => {
                  setRelationToEdit({ relation, index });
                  deleteRelationModal.handleOpen();
                }}
                onClickEdit={() => {
                  setRelationToEdit({ relation, index });
                  relationToProductModal.handleOpen();
                }}
              />
            )}
            renderDummyRow={(relation) => (
              <CourseProductRelationDummyRow
                key={relation.dummyId}
                relation={relation}
              />
            )}
          />
        </Box>
      </SimpleCard>
      <CourseFormProductRelationModal
        courseId={course.id}
        onAdd={handleCreate}
        onEdit={handleEdit}
        open={relationToProductModal.open}
        courseRelationToProduct={relationToEdit?.relation}
        handleClose={() => {
          setRelationToEdit(undefined);
          relationToProductModal.handleClose();
        }}
      />
      <AlertModal
        {...deleteRelationModal}
        title={intl.formatMessage(messages.deleteRelationModalTitle)}
        message={intl.formatMessage(messages.deleteRelationModalContent)}
        handleAccept={handleDelete}
      />
    </>
  );
}
