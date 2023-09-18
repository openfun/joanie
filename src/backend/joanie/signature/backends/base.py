"""Base Signature Backend"""


class BaseSignatureBackend:
    """
    The Signature base class.
    It contains generic methods to trigger
    the workflow process of signing a document,
    and create the invitation link.
    """

    name = "base"

    # pylint: disable=unused-argument
    def __init__(self, configuration=None, contract=None):
        self.configuration = (
            configuration.get("configuration", {}) if configuration else {}
        )

    def upload_file(self, *args, **kwargs):
        """
        Wrapper to start a signature procedure with a specifc amount
        of required signers.
        This method implies : to prepare a workflow, to upload
        a document, and start the process to sign them.
        """
        raise NotImplementedError(
            "subclasses of BaseSignatureBackend must provide a upload_file() method."
        )

    def create_invitation_link(self, recipient_email: str, *args, **kwargs):
        """
        Create invitation link to sign the document for a given email recipient.
        It will bring the user to sign every document linked to his email address.
        """
        raise NotImplementedError(
            "subclasses of BaseSignatureBackend must provide a create_invitation_link() method."
        )

    def get_signature_invitation_link(self, recipient_email: str, workflow_ids: list):
        """
        Prepare a specific invitation link that wraps more than one document to sign at once.
        """
        raise NotImplementedError(
            "subclasses of BaseSignatureBackend must provide a create_invitation_link() method."
        )

    def handle_notification(self, request):
        """
        Triggered when a notification is received by the signature provider API.
        """
        raise NotImplementedError(
            "subclasses of BaseSignatureBackend must provide a handle_notification() method."
        )

    def refuse_signature(self, recipient_email: str, workflow_ids: list):
        """
        Refuse invitation to sign a document which causes the signature to be aborted.
        """
        raise NotImplementedError(
            "subclasses of BaseSignatureBackend must provide a refuse_signature() method."
        )

    def get_document_onetime_url(self, workflow_id: str):
        """
        Download documents that were signed by all required parties.
        """
        raise NotImplementedError(
            "subclasses of BaseSignatureBackend must provide a get_document_onetime_url() method."
        )
