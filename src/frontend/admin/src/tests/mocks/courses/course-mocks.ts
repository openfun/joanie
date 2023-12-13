export const COURSE_OPTIONS_REQUEST_RESULT = {
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
                  value: "instructor",
                  display_name: "instructor",
                },
                {
                  value: "manager",
                  display_name: "manager",
                },
              ],
            },
          },
        },
      },
    },
  },
};
