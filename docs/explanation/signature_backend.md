# Signature backends

To manage signatures, Joanie relies on signature providers. That means that
we have to implement interfaces to interact with these providers. This is the
purpose of the `BaseSignatureBackend` class which offers methods that are available
when a signature procedure of a file has to be submitted, get the invitation link to
sign the file, delete a signature procedure and handle incoming notifications
from the signature provider. In this way, when implementing a new interface,
we only need to focus on the logic to normalize data from the signature provider
to Joanie.

We start with the assumption that modern e-signature providers are based on
notification webhook system. So Joanie relies on this feature to be notified
when something happens on the signature provider side for a given file (signing finished, refusing
to sign, ...)

## Reference

All signature backends are declared within `joanie.signature.backends` and must inherit from
`BaseSignatureBackend`. This class implements 4 generic methods in charge of confirming a contract
when it is signed, resetting a contract when it is refused, and there are two useful methods
in getting the setting name and to retrieve its value to configure gracefully each signature
backend classes.

- **`get_setting_name(cls, name)`**

- **`get_setting(cls, name)`**

- **`confirm_student_signature(self, reference_id)`**

- **`reset_contract(self, reference_id)`**

On the other hand, your signature backend has to implement 4 methods :

- **`submit_for_signature(self, definition: str, file_bytes: bytes, owner)`**

- **`get_signature_invitation_link(self, recipient_email: str, reference_ids: list)`**

- **`delete_signing_procedure(self, reference: str)`**

- **`handle_notification(self, request)`**

## Supported providers

You can find all signature backends at `src/backend/joanie/signature/backends`.

Currently, Joanie supports :

- [LexPersona](https://www.lex-persona.com/)

## How to

### Use signature module from local environment

To work on Joanie in a local environment, we suggest two solutions :

#### Use the `DummySignatureBackend`

In case you do not need to interact with a signature provider, we implemented
a `DummySignatureBackend` which allows you to use Joanie locally without any
configuration.

#### Use the `LexPersonaBackend`

In case you want to use this class to interact with the signature provider, make
sure that you have added all required configuration settings in your environment
variables. Here is a list of **all the required configuration** you will need to set and their explanation, **once you have subscribed with Lex Persona** :

* `JOANIE_SIGNATURE_BACKEND` : **"`joanie.signature.backends.lex_persona.LexPersonaBackend`"**

* `JOANIE_SIGNATURE_LEXPERSONA_BASE_URL` : It's the base URL provided by the signature provider.

* `JOANIE_SIGNATURE_LEXPERSONA_CONSENT_PAGE_ID` : It's a private consent page ID that is provided by the signature provider.

* `JOANIE_SIGNATURE_LEXPERSONA_SESSION_USER_ID` : It's your private user ID provided by the signature provider.

* `JOANIE_SIGNATURE_LEXPERSONA_PROFILE_ID` : It's your private signature page ID provided by the signature provider.

* `JOANIE_SIGNATURE_LEXPERSONA_TOKEN` : It's your own private token to be able to interact with the signature provider endpoints.

Futhermore, here are the common settings that are used for the signature :

* `JOANIE_SIGNATURE_VALIDITY_PERIOD` : This value is declared in seconds. It's the window of time where a file is eligible
to get signed by the signer.

* `JOANIE_SIGNATURE_TIMEOUT` : A timeout refers to the maximum amount of time in seconds for our
signature backend that will wait for the server for a response from a request before it considers the request as unsuccessful.

Here is an explanation of how we set the payload to create a signature procedure :

```python
payload = {
    "name": title,
    "description": title,
    "steps": [
        {
            "stepType": "signature",
            "recipients": recipient_data,
            "requiredRecipients": 1,
            "validityPeriod": validity_period,
            "invitePeriod": None,
            "maxInvites": 0,
            "sendDownloadLink": True,
            "allowComments": False,
            "hideAttachments": False,
            "hideWorkflowRecipients": False,
        }
    ],
    "notifiedEvents": [
        "recipientRefused",
        "workflowFinished",
    ],
    "watchers": [],
}
```
* `name` and `description` : the name that will figure on the Lex Persona platform when the signer
will accept to sign the file.
* `recipient` : awaits a list with a dictionnary where we set the signer's information.
* `requiredRecipients` : the minimum amount of signature to mark the file has completed.
* `validityPeriod` : the length of days (declared in seconds) where the file is eligible to be
signed.
* `maxInvites` : if it set to 0, it means that it will never send an email with the invitation
link. This variable is useful if you want the signature provider to send the invitation itself to
the signer. In our case, we do not need this since we give the invitation link ourselves to the
user.
* `sendDownloadLink` : if True, it sends the download link by email to the signer once the file
has been signed by the required recipients.
* `notifiedEvents` : configuration of the incoming events we await through the webhook signature
endpoint.

For more information, please [refer to the documentation](./lex-persona.md) that we have made to help you to understand each step of the their process.

## Contributing

This project is intended to be community-driven, if you are interesting by Joanie but your signature provider is not yet supported, feel free to [create an issue](https://github.com/openfun/joanie/issues/new?assignees=&labels=&template=Feature_request.md) or submit a pull request in compliance with our [best pratices](https://openfun.gitbooks.io/handbook/content).
