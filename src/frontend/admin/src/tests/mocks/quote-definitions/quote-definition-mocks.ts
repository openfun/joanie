export const QUOTE_DEFINITION_OPTIONS_REQUEST_RESULT = {
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
            value: "quote_default",
            display_name: "Quote Default",
          },
        ],
      },
    },
  },
};
