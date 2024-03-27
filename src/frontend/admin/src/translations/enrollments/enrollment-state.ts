import { defineMessages } from "react-intl";
import { EnrollmentState } from "@/services/api/models/Enrollment";

export const enrollmentStateMessages = defineMessages<EnrollmentState>({
  [EnrollmentState.SET]: {
    id: "translations.enrollment.state.set",
    defaultMessage: "Set",
    description: "Label for the SET enrollment state",
  },
  [EnrollmentState.FAILED]: {
    id: "translations.enrollment.state.failed",
    defaultMessage: "Failed",
    description: "Label for the FAILED enrollment state",
  },
});
