import { defineMessages } from "react-intl";

export const productFormMessages = defineMessages({
  microCredentialTitle: {
    id: "components.templates.products.form.sections.ProductFormTypeSection.microCredentialTitle",
    defaultMessage: "Microcredential",
    description: "Title for the credential product type",
  },
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
  certificationSectionWizardTitle: {
    id: "components.templates.products.form.translations.certificationSectionWizardTitle",
    defaultMessage: "Certification",
    description: "Title for the wizard certification section",
  },
  certificationDetailTitle: {
    id: "components.templates.products.form.translations.certificationDetailTitle",
    defaultMessage: "Certification details",
    description: "Subtitle for the certification details section",
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
  contractDefinitionOrder: {
    id: "components.templates.products.form.translations.contractDefinitionOrder",
    defaultMessage: "Contract definition for orders",
    description: "Label for the contract definition order input",
  },
  contractDefinitionOrderHelper: {
    id: "components.templates.products.form.translations.contractDefinitionOrderHelper",
    defaultMessage:
      "This is a contract template that will be used when purchasing the product through an order.",
    description: "Helper text for the contract definition order input",
  },
  contractDefinitionOrderPlaceholder: {
    id: "components.templates.products.form.translations.contractDefinitionOrderPlaceholder",
    defaultMessage: "Search a contract definition for orders",
    description: "placeholder text for the contract definition order input",
  },
  contractDefinitionBatchOrder: {
    id: "components.templates.products.form.translations.contractDefinitionBatchOrder",
    defaultMessage: "Contract definition for batch orders",
    description: "Label for the contract definition batch order input",
  },
  contractDefinitionBatchOrderHelper: {
    id: "components.templates.products.form.translations.contractDefinitionBatchOrderHelper",
    defaultMessage:
      "This is a contract template that will be used when purchasing the product through a batch order",
    description: "Helper text for the contract definition batch order input",
  },
  contractDefinitionBatchOrderPlaceholder: {
    id: "components.templates.products.form.translations.contractDefinitionBatchOrderPlaceholder",
    defaultMessage: "Search a contract definition for batch orders",
    description:
      "placeholder text for the contract definition batch order input",
  },
  instructionsTitle: {
    id: "components.templates.products.form.translations.instructionsTitle",
    defaultMessage: "Product instructions",
    description: "Title for the instruction section",
  },
  instructionsTitleHelp: {
    id: "components.templates.products.form.translations.instructionsTitleHelp",
    defaultMessage: "(click to edit)",
    description: "Help for the for the instruction section",
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
      "In this form, you can choose a course to integrate into the product as well as the associated course paths. " +
      "If you do not select any race runs, they will all be selected by default.",
    description: "Text for the alert info of the target courses form",
  },
  productCertificationFormInfo: {
    id: "components.templates.products.form.translations.productCertificationFormInfo",
    defaultMessage:
      "In this form, you can first select a certificate template then edit all informations related to the certification (skills, teachers, certification level, etc.).",
    description: "Text for the alert info of the certification form",
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
  choiceTargetCourseCourseRunModalTitle: {
    id: "components.templates.products.form.translations.choiceTargetCourseCourseRunModalTitle",
    defaultMessage: "Course run selection",
    description: "Title for the course runs selection section",
  },
  choiceTargetCourseCourseRunModalAlertContent: {
    id: "components.templates.products.form.translations.choiceTargetCourseCourseRunModalAlertContent",
    defaultMessage:
      "By default all course runs are selected, turn this switch on if you want to choose which course runs are selected.",
    description: "Content for the select course runs selection alert",
  },
  addTargetCourseCourseRunModalTitle: {
    id: "components.templates.products.form.translations.addTargetCourseCourseRunModalTitle",
    defaultMessage: "List of available course runs",
    description: "Title for the course runs selection section",
  },
  targetCourseIsGradedLabel: {
    id: "components.templates.products.form.translations.targetCourseIsGradedLabel",
    defaultMessage: "Taken into account for certification",
    description: "Label for the is graded switch",
  },
  certificationLevelLabel: {
    id: "components.templates.products.form.translations.certificationLevelLabel",
    defaultMessage: "Certification level",
    description: "Label for the certification level input",
  },
  certificationLevelHelper: {
    id: "components.templates.products.form.translations.certificationLevelHelper",
    defaultMessage:
      "Level of certification as defined by the European Qualifications Framework. The value must be between 1 and 8.",
    description: "Text helper for the certification level input",
  },
});
