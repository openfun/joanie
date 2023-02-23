#!/usr/bin/env bash

# usage: yarn generate:api:client:local [--output]

# OPTIONS:
#  --output  the path folder where types will be generated

openapi --input http://localhost:8071/v1.0/swagger/?format=openapi --output $1 --indent='2' --name ApiClientJoanie --useOptions
