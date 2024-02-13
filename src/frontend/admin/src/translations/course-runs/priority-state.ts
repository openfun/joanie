import { defineMessages } from "react-intl";
import { Priority } from "@/services/api/models/Course";

export const courseRunStateMessages = defineMessages<Priority>({
  [Priority.ONGOING_OPEN]: {
    id: "translations.courseRuns.priorityState.onGoingOpen",
    defaultMessage: "Currently open",
    description: "Label for the ON_GOING_OPEN priority",
  },
  [Priority.FUTURE_OPEN]: {
    id: "translations.courseRuns.priorityState.futureOpen",
    defaultMessage: "Future open",
    description: "Label for the FUTURE_OPEN priority",
  },
  [Priority.ARCHIVED_OPEN]: {
    id: "translations.courseRuns.priorityState.archivedOpen",
    defaultMessage: "Archived open",
    description: "Label for the ARCHIVED_OPEN priority",
  },
  [Priority.FUTURE_NOT_YET_OPEN]: {
    id: "translations.courseRuns.priorityState.futureNotYetOpen",
    defaultMessage: "Future not yet open",
    description: "Label for the FUTURE_NOT_YET_OPEN priority",
  },
  [Priority.FUTURE_CLOSED]: {
    id: "translations.courseRuns.priorityState.futureClosed",
    defaultMessage: "Future closed",
    description: "Label for the FUTURE_CLOSED priority",
  },
  [Priority.ONGOING_CLOSED]: {
    id: "translations.courseRuns.priorityState.ongoigClosed",
    defaultMessage: "Ongoing closed",
    description: "Label for the ONGOING_CLOSED priority",
  },
  [Priority.ARCHIVED_CLOSED]: {
    id: "translations.courseRuns.priorityState.archivedClosed",
    defaultMessage: "Archived closed",
    description: "Label for the ARCHIVED_CLOSED priority",
  },
  [Priority.TO_BE_SCHEDULED]: {
    id: "translations.courseRuns.priorityState.toBeScheduled",
    defaultMessage: "To be scheduled",
    description: "Label for the TO_BE_SCHEDULED priority",
  },
});
