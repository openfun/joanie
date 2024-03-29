import { defineMessages } from "react-intl";

export const enrollmentViewMessages = defineMessages({
  mainSectionTitle: {
    id: "components.templates.enrollments.view.mainSectionTitle",
    defaultMessage: "Details of an enrollment",
    description: "Title for the main section",
  },
  courseRun: {
    id: "components.templates.enrollments.view.courseRun",
    defaultMessage: "Course run",
    description: "Course run field",
  },
  user: {
    id: "components.templates.enrollments.view.user",
    defaultMessage: "User",
    description: "User field",
  },
  state: {
    id: "components.templates.enrollments.view.state",
    defaultMessage: "State",
    description: "State field",
  },
  isActive: {
    id: "components.templates.enrollments.view.isActive",
    defaultMessage: "Is active",
    description: "Is active checkbox field",
  },
  isActiveHelperText: {
    id: "components.templates.enrollments.view.isActiveHelperText",
    defaultMessage: "Checked if the user is registered for the course run.",
    description: "Is active helper text",
  },
  stateFailedMessage: {
    id: "components.templates.enrollments.view.stateFailedMessage",
    defaultMessage: "A problem occurred during enrollment on the LMS.",
    description: "Message displayed when the status is failed",
  },
  wasCreatedForOrder: {
    id: "components.templates.enrollments.view.wasCreatedForOrder",
    defaultMessage: "Was created for an order",
    description: "wasCreatedForOrder field",
  },
  wasCreatedForOrderHelperText: {
    id: "components.templates.enrollments.view.wasCreatedForOrderHelperText",
    defaultMessage:
      "Checked if the enrollment was originally created as part of an order.",
    description: "wasCreatedForOrder helper text",
  },
});
