# Api client TypeScript

Joanie can create a TypeScript client to be use in frontend applications.
This client is made with [openapi-typescript-codegen](https://github.com/ferdikoomen/openapi-typescript-codegen) and Joanie's backend openapi schema (available [here](http://localhost:8071/v1.0/swagger/?format=openapi) if you have Joanie's backend running).

## Requirements

We'll need the online openapi schema generate by swagger. Therefor you need to install [Joanie](https://github.com/openfun/joanie).

## Install openApiClientJs

```sh
$ cd src/openApiClientJS
$ yarn install
```

## Generate the client

```sh
yarn generate:api:client:local <output_path_for_generated_code>
```
