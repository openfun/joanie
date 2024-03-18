import * as React from "react";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { defineMessages, FormattedMessage, useIntl } from "react-intl";
import Box from "@mui/material/Box";
import CopyAllIcon from "@mui/icons-material/CopyAll";
import { ProductRelationToCourse } from "@/services/api/models/Relations";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { PATH_ADMIN } from "@/utils/routes/path";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import { MenuPopover } from "@/components/presentational/menu-popover/MenuPopover";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";

const messages = defineMessages({
  sectionTitle: {
    id: "components.templates.products.form.translations.courseProductRelations.sectionTitle",
    defaultMessage: "List of courses to which this product is linked",
    description: "Product course relation section title",
  },
});

type Props = {
  relations?: ProductRelationToCourse[];
};
export function ProductFormCourseProductRelations({ relations = [] }: Props) {
  const intl = useIntl();
  const copyToClipboard = useCopyToClipboard();
  return (
    <SimpleCard>
      <Box padding={4}>
        <Stack spacing={2}>
          <Typography variant="subtitle2">
            <FormattedMessage {...messages.sectionTitle} />
          </Typography>
        </Stack>
        <Stack spacing={1} mt={3}>
          {relations.map((relation) => (
            <DefaultRow
              permanentRightActions={
                relation.uri ? (
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
                ) : undefined
              }
              enableDelete={false}
              subTitle={relation.organizations
                .map((org) => org.title)
                .join(",")}
              mainTitle={
                <CustomLink href={PATH_ADMIN.courses.edit(relation.course.id)}>
                  {relation.course.title}
                </CustomLink>
              }
              key={relation.course.title}
            />
          ))}
        </Stack>
      </Box>
    </SimpleCard>
  );
}
