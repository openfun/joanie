import { defineMessages } from "react-intl";

export const productFormMessages = defineMessages({
  mainSectionWizardTitle: {
    id: "components.templates.products.form.translations.mainSectionWizardTitle",
    defaultMessage: "Main",
    description: "Title for the wizard main information section",
  },
  targetCourseSectionWizardTitle: {
    id: "components.templates.products.form.translations.targetCourseSectionWizardTitle",
    defaultMessage: "Target courses",
    description: "Title for the wizard target courses section",
  },
  relatedCourseSectionWizardTitle: {
    id: "components.templates.products.form.translations.relatedCourseSectionWizardTitle",
    defaultMessage: "Related courses",
    description: "Title for the wizard related courses section",
  },
  mainInformationTitle: {
    id: "components.templates.products.form.translations.mainInformationTitle",
    defaultMessage: "Main information's",
    description: "Title for the main information section",
  },
  productTypeLabel: {
    id: "components.templates.products.form.translations.productTypeLabel",
    defaultMessage: "Type",
    description: "Label for the product type input",
  },
  relatedCoursesHelper: {
    id: "components.templates.products.form.translations.relatedCoursesHelper",
    defaultMessage:
      "This section allows you to choose the courses to which this product will be attached. Users will therefore be " +
      "able to access this product through these courses.",
    description: "Helper text for the related courses section",
  },
  related_courses: {
    id: "components.templates.products.form.translations.related_courses",
    defaultMessage: "Related courses",
    description: "Label for the related courses input",
  },
  definition: {
    id: "components.templates.products.form.translations.definition",
    defaultMessage: "Certificate definition",
    description: "Label for the definition input",
  },
  definitionHelper: {
    id: "components.templates.products.form.translations.definitionHelper",
    defaultMessage:
      "Used for the generation of the certificate of completion of the course",
    description: "Helper text for the definition input",
  },
  financialInformationTitle: {
    id: "components.templates.products.form.translations.financialInformationTitle",
    defaultMessage: "Financial information's",
    description: "Title for the financial information section",
  },
  callToAction: {
    id: "components.templates.products.form.translations.callToAction",
    defaultMessage: "Call to action",
    description: "Label for the call to action input",
  },
  price: {
    id: "components.templates.products.form.translations.price",
    defaultMessage: "Price",
    description: "Label for the price input",
  },
  priceCurrency: {
    id: "components.templates.products.form.translations.priceCurrency",
    defaultMessage: "Price currency",
    description: "Label for the price currency input",
  },
  targetCoursesHelperSection: {
    id: "components.templates.products.form.translations.targetCoursesHelperSection",
    defaultMessage:
      "In this part, you can choose the courses contained in the product, as well as all the associated " +
      "course sessions",
    description: "Helper text for the target courses section",
  },
  targetCoursesTitle: {
    id: "components.templates.products.form.translations.targetCoursesTitle",
    defaultMessage: "Product target courses",
    description: "Title for the target courses section",
  },
  addTargetCourseButtonLabel: {
    id: "components.templates.products.form.translations.addTargetCourseButtonLabel",
    defaultMessage: "Add target course",
    description: "Label for the add target courses button",
  },
  noTargetCourses: {
    id: "components.templates.products.form.translations.noTargetCourses",
    defaultMessage:
      "No target course has been added yet. Click the button to add",
    description: "Label for the empty target course message",
  },
  addRelatedCourseButtonLabel: {
    id: "components.templates.products.form.translations.addRelatedCourseButtonLabel",
    defaultMessage: "Add related course",
    description: "Label for the add related courses button",
  },
  noRelatedCourses: {
    id: "components.templates.products.form.translations.noRelatedCourses",
    defaultMessage:
      "No related course has been added yet. Click the button to add",
    description: "Label for the empty related course message",
  },
  targetCourseRowSubTitle: {
    id: "components.templates.products.form.translations.targetCourseRowSubTitle",
    defaultMessage: `{numPhotos, plural,
      =0 {All selected course_runs.}
      other {# course runs selected.}
    }`,
    description: "Label for the use all course run checkbox",
  },
  productTargetCourseFormInfo: {
    id: "components.templates.products.form.translations.productTargetCourseFormInfo",
    defaultMessage:
      "In this form, you can choose a course to integrate it into the product as well as the associated course runs.",
    description: "Text for the alert info",
  },
  productRelatedCoursesFormInfo: {
    id: "components.templates.products.form.translations.productRelatedCoursesFormInfo",
    defaultMessage:
      "In this form, you can choose a course for which the product will be accessible, then select" +
      " all the organizations that have the right to sell this course.",
    description: "Text for the alert info",
  },
  useSpecificCourseRunsCheckboxLabel: {
    id: "components.templates.products.form.translations.useSpecificCourseRunsCheckboxLabel",
    defaultMessage: "Choose specific course-runs",
    description: "Label for the use specific course run checkbox",
  },
  addTargetCourseRelationModalTitle: {
    id: "components.templates.products.form.translations.addTargetCourseRelationModalTitle",
    defaultMessage: "Add target courses",
    description: "Title for the add target courses modal",
  },
});
