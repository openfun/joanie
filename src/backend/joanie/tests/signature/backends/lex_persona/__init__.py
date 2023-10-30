"""Test Lex persona backend"""


def get_expected_workflow_payload(workflow_status):
    """Return the expected response when fetchin a workflow"""

    return {
        "created": 1696238245608,
        "currentRecipientEmails": [],
        "currentRecipientUsers": [],
        "description": "1 rue de l'exemple, 75000 Paris",
        "email": "johndoe@example.fr",
        "firstName": "John",
        "groupId": "grp_id_fake",
        "id": "wfl_id_fake",
        "lastName": "Doe",
        "logs": [],
        "name": "Heavy Duty Wool Watch",
        "notifiedEvents": [
            "recipientRefused",
            "recipientFinished",
            "workflowStopped",
            "workflowFinished",
        ],
        "progress": 0,
        "steps": [
            {
                "allowComments": True,
                "hideAttachments": False,
                "hideWorkflowRecipients": True,
                "id": "stp_J5gCgaRRY4NHtbGs474WjMkA",
                "invitePeriod": None,
                "isFinished": False,
                "isStarted": False,
                "logs": [],
                "maxInvites": 0,
                "recipients": [
                    {
                        "consentPageId": "cop_id_fake",
                        "country": "FR",
                        "email": "johnnydoe@example.fr",
                        "firstName": "Johnny",
                        "lastName": "Doe",
                        "preferredLocale": "fr",
                    }
                ],
                "requiredRecipients": 1,
                "sendDownloadLink": True,
                "stepType": "signature",
                "validityPeriod": 86400000,
            }
        ],
        "tenantId": "ten_id_fake",
        "updated": 1696238262735,
        "userId": "usr_id_fake",
        "viewAuthorizedGroups": ["grp_id_fake"],
        "viewAuthorizedUsers": [],
        "watchers": [],
        "workflowStatus": workflow_status,
    }
