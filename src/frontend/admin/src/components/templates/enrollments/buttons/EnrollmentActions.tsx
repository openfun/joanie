import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import moment from "moment";
import CancelIcon from "@mui/icons-material/Cancel";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ButtonMenu, {
  MenuOption,
} from "@/components/presentational/button/menu/ButtonMenu";
import {
  useEnrollment,
  useEnrollments,
} from "@/hooks/useEnrollments/useEnrollments";
import { Enrollment } from "@/services/api/models/Enrollment";
import { useModal } from "@/components/presentational/modal/useModal";
import { AlertModal } from "@/components/presentational/modal/AlertModal";

const messages = defineMessages({
  enrollmentActionsLabel: {
    id: "components.templates.enrollments.buttons.enrollmentActionsButton.enrollmentActionsLabel",
    description: "Label for the actions button",
    defaultMessage: "Actions",
  },
  enroll: {
    id: "components.templates.orders.buttons.enrollmentActionsButton.enroll",
    description: "Label for the enroll enrollment action",
    defaultMessage: "Enroll",
  },
  unroll: {
    id: "components.templates.orders.buttons.enrollmentActionsButton.unroll",
    description: "Label for the unenroll enrollment action",
    defaultMessage: "unenroll",
  },
  cantEnrollMessage: {
    id: "components.templates.orders.buttons.enrollmentActionsButton.cantEnrollMessage",
    description: "Label for the can't enroll tooltip message",
    defaultMessage:
      "It's impossible to enroll because the course run is not opened for enrollment.",
  },
  validateUnrollModalTitle: {
    id: "components.templates.orders.buttons.enrollmentActionsButton.validateUnrollModalTitle",
    description:
      "Text shown when clicking on the 'unenroll' button to warn that it will not be possible to go back",
    defaultMessage: "Unenroll this user",
  },
  validateUnrollModalMessage: {
    id: "components.templates.orders.buttons.enrollmentActionsButton.validateUnrollModalMessage",
    description:
      "Text for the validate enroll modal message when the enrollment session is open",
    defaultMessage:
      "Are you sure you want to unenroll {username} to {courseRunTitle}? {br}" +
      "You can register until registration closes ({enrollmentEndDate}). After this date, it will no longer be possible to revert this action.",
  },
  validateUnrollButImpossibleToEnrollAfterModalMessage: {
    id: "components.templates.orders.buttons.enrollmentActionsButton.validateUnrollButImpossibleToEnrollAfterModalMessage",
    description:
      "Text for the validate enroll modal message when the enrollment session is close",
    defaultMessage:
      "Are you sure you want to unenroll {username} to {courseRunTitle}? {br}" +
      "The registration end was: ({enrollmentEndDate}). This date having passed, it will no longer be possible to revert this action.",
  },
});

type Props = {
  enrollment: Enrollment;
};

export default function EnrollmentActionsButton({ enrollment }: Props) {
  const intl = useIntl();
  const validateUnrollModal = useModal();
  const enrollmentsQuery = useEnrollments({}, { enabled: false });
  const enrollmentQuery = useEnrollment(enrollment.id);
  const canReactivate =
    moment(enrollment.course_run.enrollment_end).diff(moment()) > 0;

  const updateEnrollment = async (is_active: boolean) => {
    await enrollmentQuery.methods.update(
      { id: enrollment.id, is_active },
      {
        onSuccess: enrollmentsQuery.methods.invalidate,
      },
    );
  };

  const handleEnrollUnroll = async () => {
    if (enrollment.is_active) {
      validateUnrollModal.handleOpen();
      return;
    }

    await updateEnrollment(!enrollment.is_active);
  };

  const options = useMemo(() => {
    const allOptions: MenuOption[] = [];
    const isActive = enrollment.is_active;
    allOptions.push({
      icon: isActive ? <CancelIcon /> : <CheckCircleIcon />,
      isDisable: isActive ? false : !canReactivate,
      disableMessage: isActive
        ? undefined
        : intl.formatMessage(messages.cantEnrollMessage),
      mainLabel: intl.formatMessage(
        isActive ? messages.unroll : messages.enroll,
      ),
      onClick: handleEnrollUnroll,
    });
    return allOptions;
  }, [enrollment]);

  if (options.length === 0) {
    return undefined;
  }

  return (
    <>
      <ButtonMenu
        data-testid="enrollment-view-action-button"
        label={intl.formatMessage(messages.enrollmentActionsLabel)}
        id="order-view-action-button"
        variant="contained"
        color="secondary"
        options={options}
      />
      <AlertModal
        validateColorButton="error"
        validateLabel={intl.formatMessage(messages.unroll)}
        title={intl.formatMessage(messages.validateUnrollModalTitle)}
        fullWidth
        maxWidth="sm"
        handleAccept={() => updateEnrollment(!enrollment.is_active)}
        message={intl.formatMessage(
          canReactivate
            ? messages.validateUnrollModalMessage
            : messages.validateUnrollButImpossibleToEnrollAfterModalMessage,
          {
            br: (
              <>
                <br />
                <br />
              </>
            ),
            username: (
              <strong>
                {enrollment.user.full_name && enrollment.user.full_name !== ""
                  ? enrollment.user.full_name
                  : enrollment.user.username}
              </strong>
            ),
            courseRunTitle: <strong>{enrollment.course_run.title}</strong>,
            enrollmentEndDate: (
              <strong>
                {new Date(
                  enrollment.course_run.enrollment_end!,
                ).toLocaleString()}
              </strong>
            ),
          },
        )}
        {...validateUnrollModal}
      />
    </>
  );
}
