export const CERTIFICATE_DEFINITION_OPTIONS_REQUEST_RESULT = {
  actions: {
    POST: {
      template: {
        type: "choice",
        required: false,
        read_only: false,
        label: "Template to generate pdf",
        choices: [
          {
            value: "certificate",
            display_name: "Certificate",
          },
          {
            value: "degree",
            display_name: "Degree",
          },
        ],
      },
    },
  },
};
