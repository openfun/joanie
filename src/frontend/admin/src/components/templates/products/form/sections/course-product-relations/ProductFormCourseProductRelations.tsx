import * as React from "react";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { defineMessages, FormattedMessage } from "react-intl";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import { ProductRelationToCourse } from "@/services/api/models/Relations";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { PATH_ADMIN } from "@/utils/routes/path";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";

const messages = defineMessages({
  sectionTitle: {
    id: "components.templates.products.form.translations.courseProductRelations.sectionTitle",
    defaultMessage: "List of courses to which this product is linked",
    description: "Product course relation section title",
  },
  sectionAlertMessage: {
    id: "components.templates.products.form.translations.courseProductRelations.sectionAlertMessage",
    defaultMessage:
      "In this section, you have access to all courses to which this product is attached. Click on the course title to navigate to its detail.",
    description: "Product course relation section alert message",
  },
});

type Props = {
  relations?: ProductRelationToCourse[];
};
export function ProductFormCourseProductRelations({ relations = [] }: Props) {
  return (
    <SimpleCard>
      <Box padding={4}>
        <Stack spacing={2}>
          <Typography variant="subtitle2">
            <FormattedMessage {...messages.sectionTitle} />
          </Typography>
          <Alert data-testid="product-course-relation-alert" severity="info">
            <FormattedMessage {...messages.sectionAlertMessage} />
          </Alert>
        </Stack>
        <Stack spacing={1} mt={3}>
          {relations.map((relation) => (
            <DefaultRow
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
