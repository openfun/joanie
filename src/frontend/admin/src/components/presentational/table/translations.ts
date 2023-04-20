import { defineMessages } from "react-intl";

export const tableTranslations = defineMessages({
  noRows: {
    id: "components.presentational.table.translations.noRows",
    defaultMessage: "No entities to display",
    description: "Label for empty table",
  },
  rowsSelected: {
    id: "components.presentational.table.translations.oneRowSelected",
    defaultMessage:
      "{count, plural, =0 {} one {# row selected} other {# rows selected}}",
    description: "Label for empty table",
  },
  deleteModalTitle: {
    id: "components.presentational.table.translations.deleteModalTitle",
    defaultMessage: "Delete an entity",
    description: "Label for delete entity modal title",
  },
  deleteModalMessage: {
    id: "components.presentational.table.translations.deleteModalMessage",
    defaultMessage:
      "Are you sure you want to delete this entity {entityName} ?",
    description: "Main message for entity modal ",
  },
});
