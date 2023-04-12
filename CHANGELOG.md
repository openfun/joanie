# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## Added

- Add course and organization accesses with roles
- CRUD admin API for organizations, products, course runs,
  certificate definitions, courses and retrieve enabled languages
- Allow on-demand page size on the order and enrollment endpoints
- Add yarn cli to generate joanie api client in TypeScript
- Display course runs into the admin course change view
- Display password field into admin user change view
- Automatically allocate organization equitably on order creation according to
  their active order count per organization for the course/product couple
- Add many admin api filters with text search 

### Changed

- Activate pagination by default on all endpoints (20 items per page)
- Use user fullname instead of username in order confirmation email
- Rename certificate field into certificate_definition for the ProductSerializer
- Improve certificate serializer

### Removed

- Badge providers now live in the obc python package
- Remove unused `OrderLiteSerializer`

## [1.1.0] - 2023-02-22

### Changed

- Encode image in base64 in order validated mail template
- Store full name in user profile through firstname field
- Set CourseRun `is_listed` to False by default
- Improve order confirmation email template
- Include course information into course runs representation

### Added

- Add synchronization for course runs
- Add make dbshell cmd to access database in cli

### Fixed

- Catch error if the max retries synchronization webhook gets reached
- Prevent server error when CourseRun instance has no start and end dates.
- Prevent to enroll on several opened course runs of the same course
- Prevent internal server error when certificate document is unprocessable
- Fix a bug that raise an error when user is automatically enrolled to
  a course run on which they have already an inactive enrollment

## [1.0.0] - 2023-01-31

### Added

- First working version serving sellable micro-credentials for multiple
  organizations synchronized to a remote catalog

[unreleased]: https://github.com/openfun/joanie/compare/v1.1.0...main
[1.1.0]: https://github.com/openfun/joanie/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/openfun/joanie/compare/695965575b80d45c2600a1bcaf84d78bebaec1e7...v1.0.0
