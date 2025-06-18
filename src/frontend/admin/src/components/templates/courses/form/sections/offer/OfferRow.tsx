import * as React from "react";
import { ReactNode, useEffect, useState } from "react";
import Stack from "@mui/material/Stack";
import Button from "@mui/material/Button";
import { defineMessages, FormattedMessage, useIntl } from "react-intl";
import PostAddIcon from "@mui/icons-material/PostAdd";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import Box from "@mui/material/Box";
import CopyAllIcon from "@mui/icons-material/CopyAll";
import { useQuery } from "@tanstack/react-query";
import Tooltip from "@mui/material/Tooltip";
import {
  DTOOfferRule,
  OfferRule,
  OfferRuleDummy,
} from "@/services/api/models/OfferRule";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import { Offer } from "@/services/api/models/Offers";
import { useModal } from "@/components/presentational/modal/useModal";
import { CustomModal } from "@/components/presentational/modal/Modal";
import { OfferRuleForm } from "@/components/templates/courses/form/sections/offer/OfferRuleForm";
import { Maybe } from "@/types/utils";
import { useOffers } from "@/hooks/useOffer/useOffer";
import { AlertModal } from "@/components/presentational/modal/AlertModal";
import { useList } from "@/hooks/useList/useList";
import { OfferRuleRow } from "@/components/templates/courses/form/sections/offer/OfferRuleRow";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { PATH_ADMIN } from "@/utils/routes/path";
import { MenuPopover } from "@/components/presentational/menu-popover/MenuPopover";
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { OfferSource } from "@/components/templates/offers/offer/OfferList";
import { OfferRepository } from "@/services/repositories/offer/OfferRepository";

const messages = defineMessages({
  mainTitleOfferRule: {
    id: "components.templates.courses.form.offer.row.mainTitleOfferRule",
    description: "Title for the offer rule row",
    defaultMessage: "Offer rule {number}",
  },
  subTitleOfferRule: {
    id: "components.templates.courses.form.offer.row.subTitleOfferRule",
    description: "Sub title for the offer rule row",
    defaultMessage: "{reservedSeats}/{totalSeats} seats",
  },
  addOfferRuleButton: {
    id: "components.templates.courses.form.offer.row.addOfferRuleButton",
    description: "Add offer rule button label",
    defaultMessage: "Add offer rule",
  },
  offerRuleIsActiveSwitchAriaLabel: {
    id: "components.templates.courses.form.offer.row.offerRuleIsActiveSwitchAriaLabel",
    description: "Aria-label for the offer rule is active switch",
    defaultMessage: "Offer rule is active switch",
  },
  deleteOfferRuleModalTitle: {
    id: "components.templates.courses.form.offer.row.deleteOfferRuleModal",
    description: "Title for the delete offer rule modal",
    defaultMessage: "Delete an offer rule",
  },
  deleteOfferRuleModalContent: {
    id: "components.templates.courses.form.offer.row.deleteOfferRuleModalContent",
    description: "Content for the delete offer rule modal",
    defaultMessage: "Are you sure you want to delete this offer rule?",
  },
  offerDisabledActionsMessage: {
    id: "components.templates.courses.form.offer.row.offerDisabledActionsMessage",
    description: "Information message for offer disabled actions",
    defaultMessage:
      "One or more orders have already occurred for this offer, so you cannot perform this action",
  },
  addOfferRuleModalFormTitle: {
    id: "components.templates.courses.form.offer.row.addOfferRuleModalFormTitle",
    defaultMessage: "Add an offer rule",
    description: "Title for the add offer rule modal",
  },
  editOfferRuleModalFormTitle: {
    id: "components.templates.courses.form.offer.row.addOfferRuleModalFormTitle",
    defaultMessage: "Edit an offer rule",
    description: "Title for the edit offer rule modal",
  },
  generateCertificate: {
    id: "components.templates.courses.form.offer.row.generateCertificate",
    defaultMessage: "Generate certificates",
    description: "Label for the generate certificate action",
  },
  alreadyCertificateGenerationInProgress: {
    id: "components.templates.courses.form.offer.row.alreadyCertificateGenerationInProgress",
    defaultMessage: "There is already a certificate generation in progress",
    description:
      "Text when hovering over the action to generate certificates, but a generation is already in progress",
  },
});

type EditOfferRuleState = {
  offerRule: OfferRule;
  orderIndex: number;
};

type Props = {
  loading?: boolean;
  offer: Offer;
  onClickEdit: (offer: Offer) => void;
  onClickDelete: (offer: Offer) => void;
  source: OfferSource;
  invalidateCourse: () => void;
};

export function OfferRow({ offer, onClickEdit, onClickDelete, source }: Props) {
  const intl = useIntl();

  const jobQuery = useQuery({
    queryKey: ["offer-job", offer.id],
    staleTime: 0,
    queryFn: async () => {
      return OfferRepository.checkStatutCertificateGenerationProcess(offer.id);
    },
  });

  const copyToClipboard = useCopyToClipboard();
  const canEdit = offer.can_edit;
  const disabledActionsMessage = canEdit
    ? intl.formatMessage(messages.offerDisabledActionsMessage)
    : undefined;

  const [currentOfferRule, setCurrentOfferRule] =
    useState<Maybe<EditOfferRuleState>>();

  const { items: offerRuleDummyList, ...dummyListMethods } =
    useList<OfferRuleDummy>([]);

  const { items: offerRuleList, ...offerRuleListMethods } = useList<OfferRule>(
    offer.offer_rules ?? [],
  );

  const offerRuleModal = useModal();
  const deleteOfferRuleModal = useModal();

  const offerQuery = useOffers({}, { enabled: false });

  const sendGenerateCertificate = async () => {
    await OfferRepository.generateMultipleCertificate(offer.id);
    await jobQuery.refetch();
  };

  const update = (
    payload: DTOOfferRule,
    offerRule: OfferRule,
    index: number,
  ) => {
    const { offer: courseId, ...restPayload } = payload;
    const { id: offerRuleId } = offerRule;
    offerRuleListMethods.updateAt(index, {
      ...offerRule,
      ...restPayload,
      nb_available_seats:
        (offerRule.nb_available_seats ?? 0) +
        ((payload.nb_seats ?? 0) - (offerRule.nb_seats ?? 0)),
    });
    offerQuery.methods.editOfferRule(
      {
        offerId: offer.id,
        offerRuleId,
        payload: {
          ...payload,
          offer: offer.id,
        },
      },
      {
        onSuccess: (data) => {
          offerRuleListMethods.updateAt(index, data);
          setCurrentOfferRule(undefined);
        },
        onError: () => {
          offerRuleListMethods.updateAt(index, offerRule);
        },
      },
    );
  };

  const deleteOfferRule = (offerRule: OfferRule, index: number) => {
    const { id: offerRuleId } = offerRule;
    offerRuleListMethods.removeAt(index);
    offerQuery.methods.deleteOfferRule(
      {
        offerId: offer.id,
        offerRuleId,
      },
      {
        onSuccess: (data) => {
          offerRuleListMethods.updateAt(index, data);
          setCurrentOfferRule(undefined);
        },
        onError: () => {
          offerRuleListMethods.insertAt(index, offerRule);
        },
      },
    );
  };

  const create = (payload: DTOOfferRule) => {
    const dummy: OfferRuleDummy = {
      dummyId: offerRuleList.length + 1 + "",
      description: payload.description ?? null,
      nb_available_seats: payload.nb_seats ?? null,
      nb_seats: payload.nb_seats ?? null,
      start: payload.start ?? null,
      end: payload.end ?? null,
      can_edit: false,
      is_active: payload.is_active,
      discount: null,
    };

    dummyListMethods.push(dummy);
    offerQuery.methods.addOfferRule(
      {
        offerId: offer.id,
        payload,
      },
      {
        onSuccess: (data) => {
          offerRuleList.push(data);
        },
        onSettled: () => {
          dummyListMethods.clear();
        },
      },
    );
  };

  useEffect(() => {
    offerRuleListMethods.set(offer.offer_rules);
  }, [offer]);

  const getMainTitle = (): ReactNode => {
    if (source === OfferSource.PRODUCT) {
      return (
        <CustomLink href={PATH_ADMIN.courses.edit(offer.course!.id)}>
          {offer.course!.title}
        </CustomLink>
      );
    }
    return (
      <CustomLink href={PATH_ADMIN.products.edit(offer.product!.id)}>
        {offer.product!.title}
      </CustomLink>
    );
  };

  const getTitle = (): string => {
    return source === OfferSource.COURSE
      ? offer.product!.title
      : offer.course!.title;
  };

  return (
    <>
      <DefaultRow
        loading={offerQuery.states.updating}
        key={getTitle()}
        mainTitle={getMainTitle()}
        subTitle={offer.organizations.map((org) => org.title).join(",")}
        enableEdit={canEdit}
        enableDelete={canEdit}
        disableDeleteMessage={disabledActionsMessage}
        permanentRightActions={
          <>
            {jobQuery.data && (
              <Tooltip
                title={intl.formatMessage(
                  messages.alreadyCertificateGenerationInProgress,
                )}
              >
                <AccessTimeIcon
                  sx={{ ml: 1 }}
                  data-testid={`already-generate-job-${offer.id}`}
                  fontSize="medium"
                  color="disabled"
                />
              </Tooltip>
            )}
            <MenuPopover
              id={`offer-actions-${offer.id}`}
              menuItems={[
                {
                  mainLabel: intl.formatMessage(messages.generateCertificate),
                  icon: <PostAddIcon fontSize="small" />,
                  onClick: sendGenerateCertificate,
                  isDisable: jobQuery.data !== undefined,
                  disableMessage: intl.formatMessage(
                    messages.alreadyCertificateGenerationInProgress,
                  ),
                },
                {
                  mainLabel: intl.formatMessage(commonTranslations.copyUrl),
                  icon: <CopyAllIcon fontSize="small" />,
                  onClick: () => copyToClipboard(offer.uri!),
                },
              ]}
            />
          </>
        }
        disableEditMessage={disabledActionsMessage}
        onEdit={() => onClickEdit(offer)}
        onDelete={() => onClickDelete(offer)}
      >
        <Stack gap={2}>
          {offerRuleList.map((offerRule, orderIndex) => {
            return (
              <OfferRuleRow
                key={offerRule.id}
                offerRule={offerRule}
                orderIndex={orderIndex}
                onDelete={() => {
                  setCurrentOfferRule({ offerRule, orderIndex });
                  deleteOfferRuleModal.handleOpen();
                }}
                onEdit={() => {
                  setCurrentOfferRule({ offerRule, orderIndex });
                  offerRuleModal.handleOpen();
                }}
                onUpdateIsActive={(isActive) => {
                  update(
                    {
                      is_active: isActive,
                      nb_seats: offerRule.nb_seats,
                      offer: offer.id,
                      discount_id: offerRule.discount?.id ?? null,
                    },
                    { ...offerRule },
                    orderIndex,
                  );
                }}
              />
            );
          })}
          {offerRuleDummyList.map((offerRule, orderIndex) => {
            return (
              <OfferRuleRow
                key={offerRule.dummyId}
                offerRule={offerRule}
                orderIndex={offerRuleList.length + orderIndex}
              />
            );
          })}
          <Button
            onClick={offerRuleModal.handleOpen}
            size="small"
            color="primary"
          >
            <FormattedMessage {...messages.addOfferRuleButton} />
          </Button>
        </Stack>
      </DefaultRow>
      <CustomModal
        fullWidth
        maxWidth="sm"
        title={intl.formatMessage(
          currentOfferRule
            ? messages.editOfferRuleModalFormTitle
            : messages.addOfferRuleModalFormTitle,
        )}
        {...offerRuleModal}
        handleClose={() => {
          setCurrentOfferRule(undefined);
          offerRuleModal.handleClose();
        }}
      >
        <Box mt={1}>
          <OfferRuleForm
            offerRule={currentOfferRule?.offerRule}
            onSubmit={(values) => {
              offerRuleModal.handleClose();
              const payload: DTOOfferRule = {
                ...values,
                offer: offer.id,
              };
              if (currentOfferRule) {
                update(
                  payload,
                  currentOfferRule.offerRule,
                  currentOfferRule.orderIndex,
                );
              } else {
                create(payload);
              }
            }}
          />
        </Box>
      </CustomModal>

      <AlertModal
        {...deleteOfferRuleModal}
        onClose={() => {
          setCurrentOfferRule(undefined);
          deleteOfferRuleModal.handleClose();
        }}
        title={intl.formatMessage(messages.deleteOfferRuleModalTitle)}
        message={intl.formatMessage(messages.deleteOfferRuleModalContent)}
        handleAccept={() => {
          if (!currentOfferRule) {
            return;
          }
          deleteOfferRule(
            currentOfferRule?.offerRule,
            currentOfferRule?.orderIndex,
          );
        }}
      />
    </>
  );
}
