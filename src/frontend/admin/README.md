# Joanie Backoffice

This package is a next.js application coupled with Material UI which aims to provide a 
UI friendly interface to manage Joanie resources. Its purpose is to replace the raw
django admin interface to build training, manage orders, courses, users and
organizations in an easy way.

## Getting started

If you have already run Joanie through `make run`, the backoffice application should be
available at `http://localhost:8072`. The development server is run, so you can edit the
code and see the changes in real time.

You can work on the backoffice application without running the whole Joanie stack. To do
so, you have to edit the `.env` file at the root of the package then set 
`NEXT_PUBLIC_API_SOURCE` to `mocked`. This `mocked` is using [msw](https://mswjs.io/)
under the hood to catch and mock requests. Then, you can run the backoffice application
with `yarn dev`.

## Contributing

This project is intended to be community-driven, so please, do not hesitate to
get in touch if you have any question related to our implementation or design
decisions.

We try to raise our code quality standards and expect contributors to follow
the recommandations from our
[handbook](https://openfun.gitbooks.io/handbook/content).

### Testing

To test this application, we are using two frameworks : 
- **Jest** for unit testing

    To run, jest test, you just have to use `yarn test`.

- **Playwright** for end to end and integration testing

  For integration testing, you have to run `yarn test-ct`.

  Launching end to end tests requires a little bit more set-up. You have to run the
  following commands:
    ```bash
    # Install browser dependencies
    npx playwright install --with-deps chromium
    
    # Build the next application in `test` mode
    # The `test` mocks requests with predictable data
    NEXT_PUBLIC_API_SOURCE=test yarn build
    
    # And finally you are able to run end to end tests
    yarn test:e2e
    ```

## License

This work is released under the MIT License (see [LICENSE](./LICENSE)).
