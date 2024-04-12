import * as React from "react";
import { ReactNode, useEffect, useState } from "react";
import Stack from "@mui/material/Stack";
import Button from "@mui/material/Button";
import { defineMessages, FormattedMessage, useIntl } from "react-intl";

import Box from "@mui/material/Box";
import CopyAllIcon from "@mui/icons-material/CopyAll";
import {
  DTOOrderGroup,
  OrderGroup,
  OrderGroupDummy,
} from "@/services/api/models/OrderGroup";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import { CourseProductRelation } from "@/services/api/models/Relations";
import { useModal } from "@/components/presentational/modal/useModal";
import { CustomModal } from "@/components/presentational/modal/Modal";
import { OrderGroupForm } from "@/components/templates/courses/form/sections/product-relation/OrderGroupForm";
import { Maybe } from "@/types/utils";
import { useCourseProductRelations } from "@/hooks/useCourseProductRelation/useCourseProductRelation";
import { AlertModal } from "@/components/presentational/modal/AlertModal";
import { useList } from "@/hooks/useList/useList";
import { OrderGroupRow } from "@/components/templates/courses/form/sections/product-relation/OrderGroupRow";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { PATH_ADMIN } from "@/utils/routes/path";
import { MenuPopover } from "@/components/presentational/menu-popover/MenuPopover";
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { CourseProductRelationSource } from "@/components/templates/relations/course-product-relation/CourseProductRelationList";

const messages = defineMessages({
  mainTitleOrderGroup: {
    id: "components.templates.courses.form.productRelation.row.mainTitleOrderGroup",
    description: "Title for the order group row",
    defaultMessage: "Order group {number}",
  },
  subTitleOrderGroup: {
    id: "components.templates.courses.form.productRelation.row.subTitleOrderGroup",
    description: "Sub title for the order group row",
    defaultMessage: "{reservedSeats}/{totalSeats} seats",
  },
  addOrderGroupButton: {
    id: "components.templates.courses.form.productRelation.row.addOrderGroupButton",
    description: "Add order group button label",
    defaultMessage: "Add order group",
  },
  orderGroupIsActiveSwitchAriaLabel: {
    id: "components.templates.courses.form.productRelation.row.orderGroupIsActiveSwitchAriaLabel",
    description: "Aria-label for the order group is active switch",
    defaultMessage: "Order group is active switch",
  },
  deleteOrderGroupModalTitle: {
    id: "components.templates.courses.form.productRelation.row.deleteOrderGroupModal",
    description: "Title for the delete order group modal",
    defaultMessage: "Delete an order group",
  },
  deleteOrderGroupModalContent: {
    id: "components.templates.courses.form.productRelation.row.deleteOrderGroupModalContent",
    description: "Content for the delete order group modal",
    defaultMessage: "Are you sure you want to delete this order group?",
  },
  relationDisabledActionsMessage: {
    id: "components.templates.courses.form.productRelation.row.relationDisabledActionsMessage",
    description: "Information message for relation disabled actions",
    defaultMessage:
      "One or more orders have already occurred for this relationship, so you cannot perform this action",
  },
  addOrderGroupModalFormTitle: {
    id: "components.templates.courses.form.productRelation.row.addOrderGroupModalFormTitle",
    defaultMessage: "Add an order group",
    description: "Title for the add order group modal",
  },
  editOrderGroupModalFormTitle: {
    id: "components.templates.courses.form.productRelation.row.addOrderGroupModalFormTitle",
    defaultMessage: "Edit an order group",
    description: "Title for the edit order group modal",
  },
});

type EditOrderGroupState = {
  orderGroup: OrderGroup;
  orderIndex: number;
};

type Props = {
  loading?: boolean;
  relation: CourseRelationToProduct;
  onClickEdit: (relation: CourseRelationToProduct) => void;
  onClickDelete: (relation: CourseRelationToProduct) => void;
  relation: CourseProductRelation;
  onClickEdit: (relation: CourseProductRelation) => void;
  onClickDelete: (relation: CourseProductRelation) => void;
  invalidateCourse: () => void;
};

export function CourseProductRelationRow({
  relation,
  onClickEdit,
  onClickDelete,
}: Props) {
  const intl = useIntl();
  const copyToClipboard = useCopyToClipboard();
  const canEdit = relation.can_edit;
  const disabledActionsMessage = canEdit
    ? intl.formatMessage(messages.relationDisabledActionsMessage)
    : undefined;

  const [currentOrderGroup, setCurrentOrderGroup] =
    useState<Maybe<EditOrderGroupState>>();

  const { items: orderGroupDummyList, ...dummyListMethods } =
    useList<OrderGroupDummy>([]);

  const { items: orderGroupList, ...orderGroupListMethods } =
    useList<OrderGroup>(relation.order_groups ?? []);

  const orderGroupModal = useModal();
  const deleteOrderGroupModal = useModal();

  const courseProductRelationQuery = useCourseProductRelations(
    {},
    { enabled: false },
  );

  const update = (
    payload: DTOOrderGroup,
    orderGroup: OrderGroup,
    index: number,
  ) => {
    const { course_product_relation: courseId, ...restPayload } = payload;
    const { id: orderGroupId } = orderGroup;
    orderGroupListMethods.updateAt(index, {
      ...orderGroup,
      ...restPayload,
      nb_available_seats:
        orderGroup.nb_available_seats +
        (payload.nb_seats - orderGroup.nb_seats),
    });
    courseProductRelationQuery.methods.editOrderGroup(
      {
        relationId: relation.id,
        orderGroupId,
        payload: {
          ...payload,
          course_product_relation: relation.id,
        },
      },
      {
        onSuccess: (data) => {
          orderGroupListMethods.updateAt(index, data);
          setCurrentOrderGroup(undefined);
        },
        onError: () => {
          orderGroupListMethods.updateAt(index, orderGroup);
        },
      },
    );
  };

  const deleteOrderGroup = (orderGroup: OrderGroup, index: number) => {
    const { id: orderGroupId } = orderGroup;
    orderGroupListMethods.removeAt(index);
    courseProductRelationQuery.methods.deleteOrderGroup(
      {
        relationId: relation.id,
        orderGroupId,
      },
      {
        onSuccess: (data) => {
          orderGroupListMethods.updateAt(index, data);
          setCurrentOrderGroup(undefined);
        },
        onError: () => {
          orderGroupListMethods.insertAt(index, orderGroup);
        },
      },
    );
  };

  const create = (payload: DTOOrderGroup) => {
    const dummy: OrderGroupDummy = {
      dummyId: orderGroupList.length + 1 + "",
      nb_available_seats: payload.nb_seats,
      nb_seats: payload.nb_seats,
      can_edit: false,
      is_active: payload.is_active,
    };

    dummyListMethods.push(dummy);
    courseProductRelationQuery.methods.addOrderGroup(
      {
        relationId: relation.id,
        payload,
      },
      {
        onSuccess: (data) => {
          orderGroupList.push(data);
        },
        onSettled: () => {
          dummyListMethods.clear();
        },
      },
    );
  };

  useEffect(() => {
    orderGroupListMethods.set(relation.order_groups);
  }, [relation]);

  return (
    <>
      <DefaultRow
        loading={courseProductRelationQuery.states.updating}
        key={relation.product.title}
        mainTitle={
          <CustomLink href={PATH_ADMIN.products.edit(relation.product.id)}>
            {relation.product.title}
          </CustomLink>
        }
        enableEdit={canEdit}
        enableDelete={canEdit}
        disableDeleteMessage={disabledActionsMessage}
        permanentRightActions={
          <MenuPopover
            id={`course-product-relation-actions-${relation.id}`}
            menuItems={[
              {
                title: intl.formatMessage(commonTranslations.copyUrl),
                icon: <CopyAllIcon fontSize="small" />,
                onClick: () => copyToClipboard(relation.uri!),
              },
            ]}
          />
        }
        disableEditMessage={disabledActionsMessage}
        onEdit={() => onClickEdit(relation)}
        onDelete={() => onClickDelete(relation)}
        subTitle={relation.organizations.map((org) => org.title).join(",")}
      >
        <Stack gap={2}>
          {orderGroupList.map((orderGroup, orderIndex) => {
            return (
              <OrderGroupRow
                key={orderGroup.id}
                orderGroup={orderGroup}
                orderIndex={orderIndex}
                onDelete={() => {
                  setCurrentOrderGroup({ orderGroup, orderIndex });
                  deleteOrderGroupModal.handleOpen();
                }}
                onEdit={() => {
                  setCurrentOrderGroup({ orderGroup, orderIndex });
                  orderGroupModal.handleOpen();
                }}
                onUpdateIsActive={(isActive) => {
                  update(
                    {
                      is_active: isActive,
                      nb_seats: orderGroup.nb_seats,
                      course_product_relation: relation.id,
                    },
                    { ...orderGroup },
                    orderIndex,
                  );
                }}
              />
            );
          })}
          {orderGroupDummyList.map((orderGroup, orderIndex) => {
            return (
              <OrderGroupRow
                key={orderGroup.dummyId}
                orderGroup={orderGroup}
                orderIndex={orderGroupList.length + orderIndex}
              />
            );
          })}
          <Button
            onClick={orderGroupModal.handleOpen}
            size="small"
            color="primary"
          >
            <FormattedMessage {...messages.addOrderGroupButton} />
          </Button>
        </Stack>
      </DefaultRow>
      <CustomModal
        fullWidth
        maxWidth="sm"
        title={intl.formatMessage(
          currentOrderGroup
            ? messages.editOrderGroupModalFormTitle
            : messages.addOrderGroupModalFormTitle,
        )}
        {...orderGroupModal}
        handleClose={() => {
          setCurrentOrderGroup(undefined);
          orderGroupModal.handleClose();
        }}
      >
        <Box mt={1}>
          <OrderGroupForm
            orderGroup={currentOrderGroup?.orderGroup}
            onSubmit={(values) => {
              orderGroupModal.handleClose();
              const payload: DTOOrderGroup = {
                ...values,
                course_product_relation: relation.id,
              };
              if (currentOrderGroup) {
                update(
                  payload,
                  currentOrderGroup.orderGroup,
                  currentOrderGroup.orderIndex,
                );
              } else {
                create(payload);
              }
            }}
          />
        </Box>
      </CustomModal>

      <AlertModal
        {...deleteOrderGroupModal}
        onClose={() => {
          setCurrentOrderGroup(undefined);
          deleteOrderGroupModal.handleClose();
        }}
        title={intl.formatMessage(messages.deleteOrderGroupModalTitle)}
        message={intl.formatMessage(messages.deleteOrderGroupModalContent)}
        handleAccept={() => {
          if (!currentOrderGroup) {
            return;
          }
          deleteOrderGroup(
            currentOrderGroup?.orderGroup,
            currentOrderGroup?.orderIndex,
          );
        }}
      />
    </>
  );
}
