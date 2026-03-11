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
  DTOOfferingRule,
  OfferingRule,
  OfferingRuleDummy,
} from "@/services/api/models/OfferingRule";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import { Offering } from "@/services/api/models/Offerings";
import { useModal } from "@/components/presentational/modal/useModal";
import { CustomModal } from "@/components/presentational/modal/Modal";
import { OfferingRuleForm } from "@/components/templates/courses/form/sections/offering/OfferingRuleForm";
import { Maybe } from "@/types/utils";
import { useOfferings } from "@/hooks/useOffering/useOffering";
import { AlertModal } from "@/components/presentational/modal/AlertModal";
import { useList } from "@/hooks/useList/useList";
import { OfferingRuleRow } from "@/components/templates/courses/form/sections/offering/OfferingRuleRow";
import {
  DTOCreateOfferingDeepLink,
  OfferingDeepLink,
  OfferingDeepLinkDummy,
} from "@/services/api/models/OfferingDeepLink";
import { OfferingDeepLinkRow } from "@/components/templates/courses/form/sections/offering/OfferingDeepLinkRow";
import {
  OfferingDeepLinkForm,
  OfferingDeepLinkFormValues,
} from "@/components/templates/courses/form/sections/offering/OfferingDeepLinkForm";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { PATH_ADMIN } from "@/utils/routes/path";
import { MenuPopover } from "@/components/presentational/menu-popover/MenuPopover";
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { OfferingSource } from "@/components/templates/offerings/offering/OfferingList";
import { OfferingRepository } from "@/services/repositories/offering/OfferingRepository";

const messages = defineMessages({
  mainTitleOfferingRule: {
    id: "components.templates.courses.form.offering.row.mainTitleOfferingRule",
    description: "Title for the offering rule row",
    defaultMessage: "Offering rule {number}",
  },
  subTitleOfferingRule: {
    id: "components.templates.courses.form.offering.row.subTitleOfferingRule",
    description: "Sub title for the offering rule row",
    defaultMessage: "{reservedSeats}/{totalSeats} seats",
  },
  addOfferingRuleButton: {
    id: "components.templates.courses.form.offering.row.addOfferingRuleButton",
    description: "Add offering rule button label",
    defaultMessage: "Add offering rule",
  },
  offeringRuleIsActiveSwitchAriaLabel: {
    id: "components.templates.courses.form.offering.row.offeringRuleIsActiveSwitchAriaLabel",
    description: "Aria-label for the offering rule is active switch",
    defaultMessage: "Offering rule is active switch",
  },
  deleteOfferingRuleModalTitle: {
    id: "components.templates.courses.form.offering.row.deleteOfferingRuleModal",
    description: "Title for the delete offering rule modal",
    defaultMessage: "Delete an offering rule",
  },
  deleteOfferingRuleModalContent: {
    id: "components.templates.courses.form.offering.row.deleteOfferingRuleModalContent",
    description: "Content for the delete offering rule modal",
    defaultMessage: "Are you sure you want to delete this offering rule?",
  },
  offeringDisabledActionsMessage: {
    id: "components.templates.courses.form.offering.row.offeringDisabledActionsMessage",
    description: "Information message for offering disabled actions",
    defaultMessage:
      "One or more orders have already occurred for this offering, so you cannot perform this action",
  },
  addOfferingRuleModalFormTitle: {
    id: "components.templates.courses.form.offering.row.addOfferingRuleModalFormTitle",
    defaultMessage: "Add an offering rule",
    description: "Title for the add offering rule modal",
  },
  editOfferingRuleModalFormTitle: {
    id: "components.templates.courses.form.offering.row.editOfferingRuleModalFormTitle",
    defaultMessage: "Edit an offering rule",
    description: "Title for the edit offering rule modal",
  },
  generateCertificate: {
    id: "components.templates.courses.form.offering.row.generateCertificate",
    defaultMessage: "Generate certificates",
    description: "Label for the generate certificate action",
  },
  alreadyCertificateGenerationInProgress: {
    id: "components.templates.courses.form.offering.row.alreadyCertificateGenerationInProgress",
    defaultMessage: "There is already a certificate generation in progress",
    description:
      "Text when hovering over the action to generate certificates, but a generation is already in progress",
  },
  addDeepLinkButton: {
    id: "components.templates.courses.form.offering.row.addDeepLinkButton",
    description: "Add deep link button label",
    defaultMessage: "Add deep link",
  },
  addDeepLinkModalFormTitle: {
    id: "components.templates.courses.form.offering.row.addDeepLinkModalFormTitle",
    defaultMessage: "Add a deep link",
    description: "Title for the add deep link modal",
  },
  editDeepLinkModalFormTitle: {
    id: "components.templates.courses.form.offering.row.editDeepLinkModalFormTitle",
    defaultMessage: "Edit a deep link",
    description: "Title for the edit deep link modal",
  },
  deleteDeepLinkModalTitle: {
    id: "components.templates.courses.form.offering.row.deleteDeepLinkModalTitle",
    description: "Title for the delete deep link modal",
    defaultMessage: "Delete a deep link",
  },
  deleteDeepLinkModalContent: {
    id: "components.templates.courses.form.offering.row.deleteDeepLinkModalContent",
    description: "Content for the delete deep link modal",
    defaultMessage: "Are you sure you want to delete this deep link?",
  },
});

type EditOfferingRuleState = {
  offeringRule: OfferingRule;
  orderIndex: number;
};

type EditDeepLinkState = {
  deepLink: OfferingDeepLink;
  orderIndex: number;
};

type Props = {
  loading?: boolean;
  offering: Offering;
  onClickEdit: (offering: Offering) => void;
  onClickDelete: (offering: Offering) => void;
  source: OfferingSource;
  invalidateCourse: () => void;
};

export function OfferingRow({
  offering,
  onClickEdit,
  onClickDelete,
  source,
}: Props) {
  const intl = useIntl();

  const jobQuery = useQuery({
    queryKey: ["offering-job", offering.id],
    staleTime: 0,
    queryFn: async () => {
      return OfferingRepository.checkStatutCertificateGenerationProcess(
        offering.id,
      );
    },
  });

  const copyToClipboard = useCopyToClipboard();
  const canEdit = offering.can_edit;
  const disabledActionsMessage = canEdit
    ? intl.formatMessage(messages.offeringDisabledActionsMessage)
    : undefined;

  const [currentOfferingRule, setCurrentOfferingRule] =
    useState<Maybe<EditOfferingRuleState>>();

  const { items: offeringRuleDummyList, ...dummyListMethods } =
    useList<OfferingRuleDummy>([]);

  const { items: offeringRuleList, ...offeringRuleListMethods } =
    useList<OfferingRule>(offering.offering_rules ?? []);

  const offeringRuleModal = useModal();
  const deleteOfferingRuleModal = useModal();

  const deepLinkModal = useModal();
  const deleteDeepLinkModal = useModal();

  const [currentDeepLink, setCurrentDeepLink] =
    useState<Maybe<EditDeepLinkState>>();

  const deepLinksQuery = useQuery({
    queryKey: ["offering-deep-links", offering.id],
    queryFn: () => OfferingRepository.getDeepLinks(offering.id),
  });

  const { items: deepLinkDummyList, ...deepLinkDummyListMethods } =
    useList<OfferingDeepLinkDummy>([]);

  const { items: deepLinkList, ...deepLinkListMethods } =
    useList<OfferingDeepLink>(deepLinksQuery.data?.results ?? []);

  const offeringQuery = useOfferings({}, { enabled: false });

  const sendGenerateCertificate = async () => {
    await OfferingRepository.generateMultipleCertificate(offering.id);
    await jobQuery.refetch();
  };

  const update = (
    payload: DTOOfferingRule,
    offeringRule: OfferingRule,
    index: number,
  ) => {
    const { offering: courseId, ...restPayload } = payload;
    const { id: offeringRuleId } = offeringRule;
    offeringRuleListMethods.updateAt(index, {
      ...offeringRule,
      ...restPayload,
      nb_available_seats:
        (offeringRule.nb_available_seats ?? 0) +
        ((payload.nb_seats ?? 0) - (offeringRule.nb_seats ?? 0)),
    });
    offeringQuery.methods.editOfferingRule(
      {
        offeringId: offering.id,
        offeringRuleId,
        payload: {
          ...payload,
          offering: offering.id,
        },
      },
      {
        onSuccess: (data) => {
          offeringRuleListMethods.updateAt(index, data);
          setCurrentOfferingRule(undefined);
        },
        onError: () => {
          offeringRuleListMethods.updateAt(index, offeringRule);
        },
      },
    );
  };

  const deleteOfferingRule = (offeringRule: OfferingRule, index: number) => {
    const { id: offeringRuleId } = offeringRule;
    offeringQuery.methods.deleteOfferingRule(
      {
        offeringId: offering.id,
        offeringRuleId,
      },
      {
        onSuccess: (data) => {
          offeringRuleListMethods.updateAt(index, data);
          setCurrentOfferingRule(undefined);
        },
        onError: () => {
          offeringRuleListMethods.insertAt(index, offeringRule);
        },
      },
    );
  };

  const create = (payload: DTOOfferingRule) => {
    const dummy: OfferingRuleDummy = {
      dummyId: offeringRuleList.length + 1 + "",
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
    offeringQuery.methods.addOfferingRule(
      {
        offeringId: offering.id,
        payload,
      },
      {
        onSuccess: (data) => {
          offeringRuleList.push(data);
        },
        onSettled: () => {
          dummyListMethods.clear();
        },
      },
    );
  };

  const createDeepLink = (values: OfferingDeepLinkFormValues) => {
    const payload: DTOCreateOfferingDeepLink = {
      organization_id: values.organization_id,
      deep_link: values.deep_link,
    };
    const dummy: OfferingDeepLinkDummy = {
      dummyId: deepLinkList.length + 1 + "",
      organization: values.organization_id,
      deep_link: values.deep_link,
      offering: offering.id,
      is_active: false,
    };
    deepLinkDummyListMethods.push(dummy);
    offeringQuery.methods.addDeepLink(
      { offeringId: offering.id, payload },
      {
        onSettled: () => {
          deepLinkDummyListMethods.clear();
          deepLinksQuery.refetch();
        },
      },
    );
  };

  const updateDeepLink = (
    values: OfferingDeepLinkFormValues,
    deepLink: OfferingDeepLink,
    index: number,
  ) => {
    deepLinkListMethods.updateAt(index, {
      ...deepLink,
      deep_link: values.deep_link,
      is_active: values.is_active,
      organization: values.organization_id,
    });
    offeringQuery.methods.editDeepLink(
      {
        offeringId: offering.id,
        deepLinkId: deepLink.id,
        payload: {
          deep_link: values.deep_link,
          is_active: values.is_active,
          organization: values.organization_id,
        },
      },
      {
        onSuccess: (data) => {
          deepLinkListMethods.updateAt(index, data);
          setCurrentDeepLink(undefined);
        },
        onError: () => {
          deepLinkListMethods.updateAt(index, deepLink);
        },
        onSettled: () => {
          deepLinksQuery.refetch();
        },
      },
    );
  };

  const deleteDeepLink = (deepLink: OfferingDeepLink, index: number) => {
    deepLinkListMethods.removeAt(index);
    offeringQuery.methods.deleteDeepLink(
      { offeringId: offering.id, deepLinkId: deepLink.id },
      {
        onError: () => {
          deepLinkListMethods.insertAt(index, deepLink);
        },
        onSettled: () => {
          setCurrentDeepLink(undefined);
          deepLinksQuery.refetch();
        },
      },
    );
  };

  useEffect(() => {
    offeringRuleListMethods.set(offering.offering_rules);
  }, [offering]);

  useEffect(() => {
    deepLinkListMethods.set(deepLinksQuery.data?.results ?? []);
  }, [deepLinksQuery.data]);

  const getMainTitle = (): ReactNode => {
    if (source === OfferingSource.PRODUCT) {
      return (
        <CustomLink href={PATH_ADMIN.courses.edit(offering.course!.id)}>
          {offering.course!.title}
        </CustomLink>
      );
    }
    return (
      <CustomLink href={PATH_ADMIN.products.edit(offering.product!.id)}>
        {offering.product!.title}
      </CustomLink>
    );
  };

  const getTitle = (): string => {
    return source === OfferingSource.COURSE
      ? offering.product!.title
      : offering.course!.title;
  };

  return (
    <>
      <DefaultRow
        loading={offeringQuery.states.updating}
        key={getTitle()}
        mainTitle={getMainTitle()}
        subTitle={offering.organizations.map((org) => org.title).join(",")}
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
                  data-testid={`already-generate-job-${offering.id}`}
                  fontSize="medium"
                  color="disabled"
                />
              </Tooltip>
            )}
            <MenuPopover
              id={`offering-actions-${offering.id}`}
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
                  onClick: () => copyToClipboard(offering.uri!),
                },
              ]}
            />
          </>
        }
        disableEditMessage={disabledActionsMessage}
        onEdit={() => onClickEdit(offering)}
        onDelete={() => onClickDelete(offering)}
      >
        <Stack gap={2}>
          {offeringRuleList.map((offeringRule, orderIndex) => {
            return (
              <OfferingRuleRow
                key={offeringRule.id}
                offeringRule={offeringRule}
                orderIndex={orderIndex}
                onDelete={() => {
                  setCurrentOfferingRule({ offeringRule, orderIndex });
                  deleteOfferingRuleModal.handleOpen();
                }}
                onEdit={() => {
                  setCurrentOfferingRule({ offeringRule, orderIndex });
                  offeringRuleModal.handleOpen();
                }}
                onUpdateIsActive={(isActive) => {
                  update(
                    {
                      is_active: isActive,
                      nb_seats: offeringRule.nb_seats,
                      offering: offering.id,
                      discount_id: offeringRule.discount?.id ?? null,
                    },
                    { ...offeringRule },
                    orderIndex,
                  );
                }}
              />
            );
          })}
          {offeringRuleDummyList.map((offeringRule, orderIndex) => {
            return (
              <OfferingRuleRow
                key={offeringRule.dummyId}
                offeringRule={offeringRule}
                orderIndex={offeringRuleList.length + orderIndex}
              />
            );
          })}
          <Button
            onClick={offeringRuleModal.handleOpen}
            size="small"
            color="primary"
          >
            <FormattedMessage {...messages.addOfferingRuleButton} />
          </Button>
          {deepLinkList.map((deepLink, orderIndex) => (
            <OfferingDeepLinkRow
              key={deepLink.id}
              deepLink={deepLink}
              organizations={offering.organizations}
              onDelete={() => {
                setCurrentDeepLink({ deepLink, orderIndex });
                deleteDeepLinkModal.handleOpen();
              }}
              onEdit={() => {
                setCurrentDeepLink({ deepLink, orderIndex });
                deepLinkModal.handleOpen();
              }}
              onUpdateIsActive={(isActive) => {
                updateDeepLink(
                  {
                    organization_id: deepLink.organization,
                    deep_link: deepLink.deep_link,
                    is_active: isActive,
                  },
                  { ...deepLink },
                  orderIndex,
                );
              }}
            />
          ))}
          {deepLinkDummyList.map((deepLink) => (
            <OfferingDeepLinkRow
              key={deepLink.dummyId}
              deepLink={deepLink}
              organizations={offering.organizations}
            />
          ))}
          <Button
            onClick={deepLinkModal.handleOpen}
            size="small"
            color="primary"
          >
            <FormattedMessage {...messages.addDeepLinkButton} />
          </Button>
        </Stack>
      </DefaultRow>
      <CustomModal
        fullWidth
        maxWidth="sm"
        title={intl.formatMessage(
          currentOfferingRule
            ? messages.editOfferingRuleModalFormTitle
            : messages.addOfferingRuleModalFormTitle,
        )}
        {...offeringRuleModal}
        handleClose={() => {
          setCurrentOfferingRule(undefined);
          offeringRuleModal.handleClose();
        }}
      >
        <Box mt={1}>
          <OfferingRuleForm
            offeringId={offering?.id}
            offeringRule={currentOfferingRule?.offeringRule}
            onSubmit={(values) => {
              offeringRuleModal.handleClose();
              const payload: DTOOfferingRule = {
                ...values,
                offering: offering.id,
              };
              if (currentOfferingRule) {
                update(
                  payload,
                  currentOfferingRule.offeringRule,
                  currentOfferingRule.orderIndex,
                );
              } else {
                create(payload);
              }
            }}
          />
        </Box>
      </CustomModal>

      <AlertModal
        {...deleteOfferingRuleModal}
        onClose={() => {
          setCurrentOfferingRule(undefined);
          deleteOfferingRuleModal.handleClose();
        }}
        title={intl.formatMessage(messages.deleteOfferingRuleModalTitle)}
        message={intl.formatMessage(messages.deleteOfferingRuleModalContent)}
        handleAccept={() => {
          if (!currentOfferingRule) {
            return;
          }
          deleteOfferingRule(
            currentOfferingRule?.offeringRule,
            currentOfferingRule?.orderIndex,
          );
        }}
      />

      <CustomModal
        fullWidth={true}
        maxWidth="sm"
        title={intl.formatMessage(
          currentDeepLink
            ? messages.editDeepLinkModalFormTitle
            : messages.addDeepLinkModalFormTitle,
        )}
        {...deepLinkModal}
        handleClose={() => {
          setCurrentDeepLink(undefined);
          deepLinkModal.handleClose();
        }}
      >
        <Box mt={1}>
          <OfferingDeepLinkForm
            deepLink={currentDeepLink?.deepLink}
            organizations={offering.organizations}
            onSubmit={(values) => {
              deepLinkModal.handleClose();
              if (currentDeepLink) {
                updateDeepLink(
                  values,
                  currentDeepLink.deepLink,
                  currentDeepLink.orderIndex,
                );
              } else {
                createDeepLink(values);
              }
            }}
          />
        </Box>
      </CustomModal>

      <AlertModal
        {...deleteDeepLinkModal}
        onClose={() => {
          setCurrentDeepLink(undefined);
          deleteDeepLinkModal.handleClose();
        }}
        title={intl.formatMessage(messages.deleteDeepLinkModalTitle)}
        message={intl.formatMessage(messages.deleteDeepLinkModalContent)}
        handleAccept={() => {
          if (!currentDeepLink) {
            return;
          }
          deleteDeepLink(currentDeepLink.deepLink, currentDeepLink.orderIndex);
        }}
      />
    </>
  );
}
