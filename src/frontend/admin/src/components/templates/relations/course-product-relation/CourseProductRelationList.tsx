import * as React from "react";
import { useEffect, useMemo } from "react";
import { defineMessages, FormattedMessage, useIntl } from "react-intl";
import Stack from "@mui/material/Stack";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { useModal } from "@/components/presentational/modal/useModal";
import { CourseFormProductRelationModal } from "@/components/templates/courses/form/product-relation/CourseFormProductRelationModal";
import { CourseProductRelationRow } from "@/components/templates/courses/form/sections/product-relation/CourseProductRelationRow";
import { CourseProductRelation } from "@/services/api/models/Relations";
import { CourseProductRelationDummyRow } from "@/components/templates/courses/form/sections/product-relation/CourseProductRelationDummyRow";
import { AlertModal } from "@/components/presentational/modal/AlertModal";
import { CustomList } from "@/components/presentational/list/CustomList";
import { useCourseProductRelationList } from "@/components/templates/relations/course-product-relation/useCourseProductRelationList";

export enum CourseProductRelationSource {
  PRODUCT = "product",
  COURSE = "course",
}

const messages = defineMessages({
  addRelationButtonLabel: {
    id: "components.templates.relations.courseProductRelation.CourseProductRelationList.addRelationButtonLabel",
    defaultMessage: "Add relation",
    description: "Label for the product relation subheader form",
  },
  deleteRelationModalTitle: {
    id: "components.templates.relations.courseProductRelation.CourseProductRelationList.deleteRelationModalTitle",
    description: "Title for the delete relation modal",
    defaultMessage: "Delete product relationship",
  },
  deleteRelationModalContent: {
    id: "components.templates.relations.courseProductRelation.CourseProductRelationList.deleteRelationModalContent",
    description: "Content for the delete relation modal",
    defaultMessage: "Are you sure you want to delete this relation?",
  },
  emptyCourseList: {
    id: "components.templates.relations.courseProductRelation.CourseProductRelationList.emptyCourseList",
    description:
      "Message when the course relation product list is empty inside the course form",
    defaultMessage:
      "No product relationships have been created for this course",
  },
  titleCourseHeader: {
    id: "components.templates.relations.courseProductRelation.CourseProductRelationList.titleCourseHeader",
    description:
      "Title for the course relation product list inside the course form",
    defaultMessage: "Relation to products",
  },
  emptyProductList: {
    id: "components.templates.relations.courseProductRelation.CourseProductRelationList.emptyProductList",
    description:
      "Message when the course relation product list is empty inside the product form",
    defaultMessage:
      "No course relationships have been created for this product",
  },
  titleProductHeader: {
    id: "components.templates.relations.courseProductRelation.CourseProductRelationList.titleProductHeader",
    description:
      "Title for the course relation product list inside the product form",
    defaultMessage: "Relation to courses",
  },
});

type BaseProps = {
  relations: CourseProductRelation[];
  invalidate: () => void;
};

type PropsWithCourse = BaseProps & {
  courseId: string;
  productId?: string;
};

type PropsWithProduct = BaseProps & {
  courseId?: string;
  productId: string;
};

export function CourseProductRelationList({
  relations = [],
  invalidate,
  ...props
}: PropsWithCourse | PropsWithProduct) {
  const intl = useIntl();
  const deleteRelationModal = useModal();

  const source: CourseProductRelationSource = useMemo(() => {
    return props.productId
      ? CourseProductRelationSource.PRODUCT
      : CourseProductRelationSource.COURSE;
  }, [props.productId, props.courseId]);
  const isCourse = source === CourseProductRelationSource.COURSE;

  const listUtils = useCourseProductRelationList({
    relations,
    invalidate,
  });

  useEffect(() => {
    listUtils.relationList.set(relations ?? []);
  }, [relations]);

  return (
    <>
      <SimpleCard>
        <Box padding={3}>
          <Stack padding={3} gap={2}>
            <Box
              sx={{
                display: "flex",
                flexDirection: { xs: "column", md: "row" },
                justifyContent: { xs: "flex-start", md: "space-between" },
                alignItems: { xs: "flex-start", md: "center" },
              }}
            >
              <Typography variant="h6">
                <FormattedMessage
                  {...(isCourse
                    ? messages.titleCourseHeader
                    : messages.titleProductHeader)}
                />
              </Typography>
              <Button
                size="small"
                variant="contained"
                sx={{ mt: { xs: 1 } }}
                onClick={listUtils.modalForm.handleOpen}
              >
                <FormattedMessage {...messages.addRelationButtonLabel} />
              </Button>
            </Box>
          </Stack>
          <CustomList
            emptyListMessage={intl.formatMessage(
              isCourse ? messages.emptyCourseList : messages.emptyProductList,
            )}
            rows={listUtils.relationList.items}
            dummyRows={listUtils.dummyRelationList.items}
            dummyRowsPosition="top"
            renderRow={(relation, index) => (
              <CourseProductRelationRow
                source={source}
                key={relation.id}
                invalidateCourse={invalidate}
                relation={relation}
                onClickDelete={() => {
                  listUtils.setRelationToEdit({ relation, index });
                  deleteRelationModal.handleOpen();
                }}
                onClickEdit={() => {
                  listUtils.setRelationToEdit({ relation, index });
                  listUtils.modalForm.handleOpen();
                }}
              />
            )}
            renderDummyRow={(relation) => (
              <CourseProductRelationDummyRow
                key={relation.dummyId}
                source={source}
                relation={relation}
              />
            )}
          />
        </Box>
      </SimpleCard>
      <CourseFormProductRelationModal
        courseId={props.courseId}
        productId={props.productId}
        open={listUtils.modalForm.open}
        relation={listUtils.relationToEdit?.relation}
        onSubmitForm={listUtils.onSubmit}
        handleClose={() => {
          listUtils.setRelationToEdit(undefined);
          listUtils.modalForm.handleClose();
        }}
      />
      <AlertModal
        {...deleteRelationModal}
        title={intl.formatMessage(messages.deleteRelationModalTitle)}
        message={intl.formatMessage(messages.deleteRelationModalContent)}
        handleAccept={listUtils.handleDelete}
      />
    </>
  );
}
