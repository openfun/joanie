import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import SchoolIcon from "@mui/icons-material/School";
import Tooltip from "@mui/material/Tooltip";
import {
  ProductTargetCourseRelation,
  ProductTargetCourseRelationOptionalId,
} from "@/services/api/models/ProductTargetCourseRelation";
import { productFormMessages } from "@/components/templates/products/form/translations";
import { DndDefaultRowProps } from "@/components/presentational/dnd/DndDefaultRow";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { PATH_ADMIN } from "@/utils/routes/path";

const messages = defineMessages({
  isGradedTooltip: {
    id: "components.templates.products.form.sections.targetCourses.ProductFormTargetCourseRow.isGradedTooltip",
    description: "Label for the is graded tooltip",
    defaultMessage: "Taken into account for certification",
  },
});

type Props = Omit<DndDefaultRowProps, "mainTitle"> & {
  item: ProductTargetCourseRelation | ProductTargetCourseRelationOptionalId;
};

const isRelation = (
  item: ProductTargetCourseRelation | ProductTargetCourseRelationOptionalId,
): item is ProductTargetCourseRelation => {
  return "id" in item;
};

export function ProductFormTargetCourseRow({ item, ...props }: Props) {
  const intl = useIntl();
  const isDummy = !isRelation(item);

  return (
    <DefaultRow
      {...props}
      testId={`${isDummy ? "dummy" : "item"}-product-target-course-${
        item.course.id
      }`}
      enableEdit={item.id !== undefined}
      enableDelete={item.id !== undefined}
      mainTitle={
        <CustomLink href={PATH_ADMIN.courses.edit(item.course.id)}>
          {item.course.title}
        </CustomLink>
      }
      permanentRightActions={
        item.is_graded ? (
          <Tooltip title={intl.formatMessage(messages.isGradedTooltip)}>
            <SchoolIcon />
          </Tooltip>
        ) : undefined
      }
      subTitle={intl.formatMessage(
        productFormMessages.targetCourseRowSubTitle,
        { numPhotos: item.course_runs.length },
      )}
    />
  );
}
