import * as React from "react";
import { useEffect, useMemo } from "react";
import { defineMessages, FormattedMessage, useIntl } from "react-intl";
import Stack from "@mui/material/Stack";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { useModal } from "@/components/presentational/modal/useModal";
import { OfferFormModal } from "@/components/templates/courses/form/offer/OfferFormModal";
import { OfferRow } from "@/components/templates/courses/form/sections/offer/OfferRow";
import { Offer } from "@/services/api/models/Offers";
import { OfferDummyRow } from "@/components/templates/courses/form/sections/offer/OfferDummyRow";
import { AlertModal } from "@/components/presentational/modal/AlertModal";
import { CustomList } from "@/components/presentational/list/CustomList";
import { useOfferList } from "@/components/templates/offers/offer/useOfferList";

export enum OfferSource {
  PRODUCT = "product",
  COURSE = "course",
}

const messages = defineMessages({
  addOfferButtonLabel: {
    id: "components.templates.offers.offer.OfferList.addOfferButtonLabel",
    defaultMessage: "Add offer",
    description: "Label for the product offer subheader form",
  },
  deleteOfferModalTitle: {
    id: "components.templates.offers.offer.OfferList.deleteOfferModalTitle",
    description: "Title for the delete offer modal",
    defaultMessage: "Delete offer",
  },
  deleteOfferModalContent: {
    id: "components.templates.offers.offer.OfferList.deleteOfferModalContent",
    description: "Content for the delete offer modal",
    defaultMessage: "Are you sure you want to delete this offer?",
  },
  emptyCourseList: {
    id: "components.templates.offers.offer.OfferList.emptyCourseList",
    description: "Message when the offer list is empty inside the course form",
    defaultMessage: "No offer have been created for this course",
  },
  titleCourseHeader: {
    id: "components.templates.offers.offer.OfferList.titleCourseHeader",
    description: "Title for the offer list inside the course form",
    defaultMessage: "Offers",
  },
  emptyProductList: {
    id: "components.templates.offers.offer.OfferList.emptyProductList",
    description:
      "Message when the course offer product list is empty inside the product form",
    defaultMessage: "No offer have been created for this product",
  },
  titleProductHeader: {
    id: "components.templates.offers.offer.OfferList.titleProductHeader",
    description:
      "Title for the course offer product list inside the product form",
    defaultMessage: "Offers",
  },
});

type BaseProps = {
  offers: Offer[];
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

export function OfferList({
  offers = [],
  invalidate,
  ...props
}: PropsWithCourse | PropsWithProduct) {
  const intl = useIntl();
  const deleteOfferModal = useModal();

  const source: OfferSource = useMemo(() => {
    return props.productId ? OfferSource.PRODUCT : OfferSource.COURSE;
  }, [props.productId, props.courseId]);
  const isCourse = source === OfferSource.COURSE;

  const listUtils = useOfferList({
    offers,
    invalidate,
  });

  useEffect(() => {
    listUtils.offerList.set(offers ?? []);
  }, [offers]);

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
                <FormattedMessage {...messages.addOfferButtonLabel} />
              </Button>
            </Box>
          </Stack>
          <CustomList
            emptyListMessage={intl.formatMessage(
              isCourse ? messages.emptyCourseList : messages.emptyProductList,
            )}
            rows={listUtils.offerList.items}
            dummyRows={listUtils.dummyOfferList.items}
            dummyRowsPosition="top"
            renderRow={(offer, index) => (
              <OfferRow
                source={source}
                key={offer.id}
                invalidateCourse={invalidate}
                offer={offer}
                onClickDelete={() => {
                  listUtils.setOfferToEdit({ offer, index });
                  deleteOfferModal.handleOpen();
                }}
                onClickEdit={() => {
                  listUtils.setOfferToEdit({ offer, index });
                  listUtils.modalForm.handleOpen();
                }}
              />
            )}
            renderDummyRow={(offer) => (
              <OfferDummyRow
                key={offer.dummyId}
                source={source}
                offer={offer}
              />
            )}
          />
        </Box>
      </SimpleCard>
      <OfferFormModal
        courseId={props.courseId}
        productId={props.productId}
        open={listUtils.modalForm.open}
        offer={listUtils.offerToEdit?.offer}
        onSubmitForm={listUtils.onSubmit}
        handleClose={() => {
          listUtils.setOfferToEdit(undefined);
          listUtils.modalForm.handleClose();
        }}
      />
      <AlertModal
        {...deleteOfferModal}
        title={intl.formatMessage(messages.deleteOfferModalTitle)}
        message={intl.formatMessage(messages.deleteOfferModalContent)}
        handleAccept={listUtils.handleDelete}
      />
    </>
  );
}
