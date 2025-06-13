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
import { CourseProductRelation } from "@/services/api/models/Relations";
import { useModal } from "@/components/presentational/modal/useModal";
import { CustomModal } from "@/components/presentational/modal/Modal";
import { OfferRuleForm } from "@/components/templates/courses/form/sections/product-relation/OfferRuleForm";
import { Maybe } from "@/types/utils";
import { useCourseProductRelations } from "@/hooks/useCourseProductRelation/useCourseProductRelation";
import { AlertModal } from "@/components/presentational/modal/AlertModal";
import { useList } from "@/hooks/useList/useList";
import { OfferRuleRow } from "@/components/templates/courses/form/sections/product-relation/OfferRuleRow";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { PATH_ADMIN } from "@/utils/routes/path";
import { MenuPopover } from "@/components/presentational/menu-popover/MenuPopover";
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { CourseProductRelationSource } from "@/components/templates/relations/course-product-relation/CourseProductRelationList";
import { CourseProductRelationRepository } from "@/services/repositories/course-product-relation/CourseProductRelationRepository";

const messages = defineMessages({
  mainTitleOfferRule: {
    id: "components.templates.courses.form.productRelation.row.mainTitleOfferRule",
    description: "Title for the offer rule row",
    defaultMessage: "Offer rule {number}",
  },
  subTitleOfferRule: {
    id: "components.templates.courses.form.productRelation.row.subTitleOfferRule",
    description: "Sub title for the offer rule row",
    defaultMessage: "{reservedSeats}/{totalSeats} seats",
  },
  addOfferRuleButton: {
    id: "components.templates.courses.form.productRelation.row.addOfferRuleButton",
    description: "Add offer rule button label",
    defaultMessage: "Add offer rule",
  },
  offerRuleIsActiveSwitchAriaLabel: {
    id: "components.templates.courses.form.productRelation.row.offerRuleIsActiveSwitchAriaLabel",
    description: "Aria-label for the offer rule is active switch",
    defaultMessage: "Offer rule is active switch",
  },
  deleteOfferRuleModalTitle: {
    id: "components.templates.courses.form.productRelation.row.deleteOfferRuleModal",
    description: "Title for the delete offer rule modal",
    defaultMessage: "Delete an offer rule",
  },
  deleteOfferRuleModalContent: {
    id: "components.templates.courses.form.productRelation.row.deleteOfferRuleModalContent",
    description: "Content for the delete offer rule modal",
    defaultMessage: "Are you sure you want to delete this offer rule?",
  },
  relationDisabledActionsMessage: {
    id: "components.templates.courses.form.productRelation.row.relationDisabledActionsMessage",
    description: "Information message for relation disabled actions",
    defaultMessage:
      "One or more orders have already occurred for this relationship, so you cannot perform this action",
  },
  addOfferRuleModalFormTitle: {
    id: "components.templates.courses.form.productRelation.row.addOfferRuleModalFormTitle",
    defaultMessage: "Add an offer rule",
    description: "Title for the add offer rule modal",
  },
  editOfferRuleModalFormTitle: {
    id: "components.templates.courses.form.productRelation.row.addOfferRuleModalFormTitle",
    defaultMessage: "Edit an offer rule",
    description: "Title for the edit offer rule modal",
  },
  generateCertificate: {
    id: "components.templates.courses.form.productRelation.row.generateCertificate",
    defaultMessage: "Generate certificates",
    description: "Label for the generate certificate action",
  },
  alreadyCertificateGenerationInProgress: {
    id: "components.templates.courses.form.productRelation.row.alreadyCertificateGenerationInProgress",
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
  relation: CourseProductRelation;
  onClickEdit: (relation: CourseProductRelation) => void;
  onClickDelete: (relation: CourseProductRelation) => void;
  source: CourseProductRelationSource;
  invalidateCourse: () => void;
};

export function CourseProductRelationRow({
  relation,
  onClickEdit,
  onClickDelete,
  source,
}: Props) {
  const intl = useIntl();

  const jobQuery = useQuery({
    queryKey: ["course-product-relation-job", relation.id],
    staleTime: 0,
    queryFn: async () => {
      return CourseProductRelationRepository.checkStatutCertificateGenerationProcess(
        relation.id,
      );
    },
  });

  const copyToClipboard = useCopyToClipboard();
  const canEdit = relation.can_edit;
  const disabledActionsMessage = canEdit
    ? intl.formatMessage(messages.relationDisabledActionsMessage)
    : undefined;

  const [currentOfferRule, setCurrentOfferRule] =
    useState<Maybe<EditOfferRuleState>>();

  const { items: offerRuleDummyList, ...dummyListMethods } =
    useList<OfferRuleDummy>([]);

  const { items: offerRuleList, ...offerRuleListMethods } = useList<OfferRule>(
    relation.offer_rules ?? [],
  );

  const offerRuleModal = useModal();
  const deleteOfferRuleModal = useModal();

  const courseProductRelationQuery = useCourseProductRelations(
    {},
    { enabled: false },
  );

  const sendGenerateCertificate = async () => {
    await CourseProductRelationRepository.generateMultipleCertificate(
      relation.id,
    );
    await jobQuery.refetch();
  };

  const update = (
    payload: DTOOfferRule,
    offerRule: OfferRule,
    index: number,
  ) => {
    const { course_product_relation: courseId, ...restPayload } = payload;
    const { id: offerRuleId } = offerRule;
    offerRuleListMethods.updateAt(index, {
      ...offerRule,
      ...restPayload,
      nb_available_seats:
        (offerRule.nb_available_seats ?? 0) +
        ((payload.nb_seats ?? 0) - (offerRule.nb_seats ?? 0)),
    });
    courseProductRelationQuery.methods.editOfferRule(
      {
        relationId: relation.id,
        offerRuleId,
        payload: {
          ...payload,
          course_product_relation: relation.id,
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
    courseProductRelationQuery.methods.deleteOfferRule(
      {
        relationId: relation.id,
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
    courseProductRelationQuery.methods.addOfferRule(
      {
        relationId: relation.id,
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
    offerRuleListMethods.set(relation.offer_rules);
  }, [relation]);

  const getMainTitle = (): ReactNode => {
    if (source === CourseProductRelationSource.PRODUCT) {
      return (
        <CustomLink href={PATH_ADMIN.courses.edit(relation.course!.id)}>
          {relation.course!.title}
        </CustomLink>
      );
    }
    return (
      <CustomLink href={PATH_ADMIN.products.edit(relation.product!.id)}>
        {relation.product!.title}
      </CustomLink>
    );
  };

  const getTitle = (): string => {
    return source === CourseProductRelationSource.COURSE
      ? relation.product!.title
      : relation.course!.title;
  };

  return (
    <>
      <DefaultRow
        loading={courseProductRelationQuery.states.updating}
        key={getTitle()}
        mainTitle={getMainTitle()}
        subTitle={relation.organizations.map((org) => org.title).join(",")}
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
                  data-testid={`already-generate-job-${relation.id}`}
                  fontSize="medium"
                  color="disabled"
                />
              </Tooltip>
            )}
            <MenuPopover
              id={`course-product-relation-actions-${relation.id}`}
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
                  onClick: () => copyToClipboard(relation.uri!),
                },
              ]}
            />
          </>
        }
        disableEditMessage={disabledActionsMessage}
        onEdit={() => onClickEdit(relation)}
        onDelete={() => onClickDelete(relation)}
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
                      course_product_relation: relation.id,
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
                course_product_relation: relation.id,
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
