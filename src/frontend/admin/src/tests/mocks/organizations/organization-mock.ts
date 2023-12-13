export const ORGANIZATION_OPTIONS_REQUEST_RESULT = {
  actions: {
    POST: {
      accesses: {
        child: {
          children: {
            role: {
              choices: [
                {
                  value: "owner",
                  display_name: "owner",
                },
                {
                  value: "administrator",
                  display_name: "administrator",
                },
                {
                  value: "member",
                  display_name: "member",
                },
              ],
            },
          },
        },
      },
    },
  },
};
