export const CONTRACT_DEFINITION_OPTIONS_REQUEST_RESULT = {
  actions: {
    POST: {
      language: {
        choices: [
          {
            value: "en-us",
            display_name: "English",
          },
          {
            value: "fr-fr",
            display_name: "French",
          },
        ],
      },
      name: {
        choices: [
          {
            value: "contract_definition_default",
            display_name: "Contract Definition Default",
          },
          {
            value: "contract_definition_unicamp",
            display_name: "Contract Definition Unicamp",
          },
          {
            value: "professional_training_agreement_default",
            display_name: "Professional Training Agreement Default",
          },
          {
            value: "professional_training_agreement_unicamp",
            display_name: "Professional Training Agreement Unicamp",
          },
        ],
      },
    },
  },
};
