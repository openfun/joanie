"""Test suite of withdrawal email utility methods"""

from django.test import TestCase

from joanie.core.utils.emails import _prepare_subject_withdrawal_email


class WithdrawalEmailUtilityTest(TestCase):
    """Test suite of withdrawal email utility methods"""

    def test_utils_withdrawal_email_prepare_subject_withdrawal_email(self):
        """
        When passing the template name and the index, the method
        `_prepare_subject_withdrawal_email` shoudl return the appropriate subject.
        """
        subject_request_0 = _prepare_subject_withdrawal_email("withdrawal_request", 0)

        self.assertEqual(
            subject_request_0, "Withdrawal request – Acknowledgement of receipt"
        )

        subject_request_1 = _prepare_subject_withdrawal_email("withdrawal_request", 1)

        self.assertEqual(subject_request_1, "Withdrawal - Validation request")

        subject_confirmation_0 = _prepare_subject_withdrawal_email(
            "withdrawal_confirmation", 0
        )

        self.assertEqual(
            subject_confirmation_0,
            "Confirmation of withdrawal - Acknowledgement of receipt",
        )

        subject_confirmation_1 = _prepare_subject_withdrawal_email(
            "withdrawal_confirmation", 1
        )

        self.assertEqual(
            subject_confirmation_1,
            "Learner withdrawal - Notification of order cancellation",
        )

        subject_rejection_0 = _prepare_subject_withdrawal_email(
            "withdrawal_rejection", 0
        )

        self.assertEqual(
            subject_rejection_0, "Withdrawal request rejected – Order remains active"
        )

        subject_rejection_1 = _prepare_subject_withdrawal_email(
            "withdrawal_rejection", 1
        )

        self.assertEqual(
            subject_rejection_1, "Withdrawal request rejected – Order remains active"
        )
