import * as React from "react";
import { useEffect, useMemo } from "react";
import { defineMessages, FormattedMessage, useIntl } from "react-intl";
import Stack from "@mui/material/Stack";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { useModal } from "@/components/presentational/modal/useModal";
import { OfferingFormModal } from "@/components/templates/courses/form/offering/OfferingFormModal";
import { OfferingRow } from "@/components/templates/courses/form/sections/offering/OfferingRow";
import { Offering } from "@/services/api/models/Offerings";
import { OfferingDummyRow } from "@/components/templates/courses/form/sections/offering/OfferingDummyRow";
import { AlertModal } from "@/components/presentational/modal/AlertModal";
import { CustomList } from "@/components/presentational/list/CustomList";
import { useOfferingList } from "@/components/templates/offerings/offering/useOfferingList";

export enum OfferingSource {
  PRODUCT = "product",
  COURSE = "course",
}

const messages = defineMessages({
  addOfferingButtonLabel: {
    id: "components.templates.offerings.offering.OfferingList.addOfferingButtonLabel",
    defaultMessage: "Add offering",
    description: "Label for the product offering subheader form",
  },
  deleteOfferingModalTitle: {
    id: "components.templates.offerings.offering.OfferingList.deleteOfferingModalTitle",
    description: "Title for the delete offering modal",
    defaultMessage: "Delete offering",
  },
  deleteOfferingModalContent: {
    id: "components.templates.offerings.offering.OfferingList.deleteOfferingModalContent",
    description: "Content for the delete offering modal",
    defaultMessage: "Are you sure you want to delete this offering?",
  },
  emptyCourseList: {
    id: "components.templates.offerings.offering.OfferingList.emptyCourseList",
    description:
      "Message when the offering list is empty inside the course form",
    defaultMessage: "No offering have been created for this course",
  },
  titleCourseHeader: {
    id: "components.templates.offerings.offering.OfferingList.titleCourseHeader",
    description: "Title for the offering list inside the course form",
    defaultMessage: "Offerings",
  },
  emptyProductList: {
    id: "components.templates.offerings.offering.OfferingList.emptyProductList",
    description:
      "Message when the course offering product list is empty inside the product form",
    defaultMessage: "No offering have been created for this product",
  },
  titleProductHeader: {
    id: "components.templates.offerings.offering.OfferingList.titleProductHeader",
    description:
      "Title for the course offering product list inside the product form",
    defaultMessage: "Offerings",
  },
});

type BaseProps = {
  offerings: Offering[];
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

export function OfferingList({
  offerings = [],
  invalidate,
  ...props
}: PropsWithCourse | PropsWithProduct) {
  const intl = useIntl();
  const deleteOfferingModal = useModal();

  const source: OfferingSource = useMemo(() => {
    return props.productId ? OfferingSource.PRODUCT : OfferingSource.COURSE;
  }, [props.productId, props.courseId]);
  const isCourse = source === OfferingSource.COURSE;

  const listUtils = useOfferingList({
    offerings,
    invalidate,
  });

  useEffect(() => {
    listUtils.offeringList.set(offerings ?? []);
  }, [offerings]);

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
                <FormattedMessage {...messages.addOfferingButtonLabel} />
              </Button>
            </Box>
          </Stack>
          <CustomList
            emptyListMessage={intl.formatMessage(
              isCourse ? messages.emptyCourseList : messages.emptyProductList,
            )}
            rows={listUtils.offeringList.items}
            dummyRows={listUtils.dummyOfferingList.items}
            dummyRowsPosition="top"
            renderRow={(offering, index) => (
              <OfferingRow
                source={source}
                key={offering.id}
                invalidateCourse={invalidate}
                offering={offering}
                onClickDelete={() => {
                  listUtils.setOfferingToEdit({ offering, index });
                  deleteOfferingModal.handleOpen();
                }}
                onClickEdit={() => {
                  listUtils.setOfferingToEdit({ offering, index });
                  listUtils.modalForm.handleOpen();
                }}
              />
            )}
            renderDummyRow={(offering) => (
              <OfferingDummyRow
                key={offering.dummyId}
                source={source}
                offering={offering}
              />
            )}
          />
        </Box>
      </SimpleCard>
      <OfferingFormModal
        courseId={props.courseId}
        productId={props.productId}
        open={listUtils.modalForm.open}
        offering={listUtils.offeringToEdit?.offering}
        onSubmitForm={listUtils.onSubmit}
        handleClose={() => {
          listUtils.setOfferingToEdit(undefined);
          listUtils.modalForm.handleClose();
        }}
      />
      <AlertModal
        {...deleteOfferingModal}
        title={intl.formatMessage(messages.deleteOfferingModalTitle)}
        message={intl.formatMessage(messages.deleteOfferingModalContent)}
        handleAccept={listUtils.handleDelete}
      />
    </>
  );
}
