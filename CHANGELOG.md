# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## Added

- Add a route to reorder target_courses
- Add target_course route and list view for products
- Add multiples product, order, certificates and enrollment in the database
  that's initialized with the `make demo-dev`
- Add client api filter to filter `Order` resource by `product__type` 
- Add a backoffice redirect view to redirect to the frontend admin backoffice
- Add filters to CourseRun list for a given course on admin api
- Allow issuing a certificate directly for an enrollment (without an order)
- Generate certificates for products of type `certificate`
- Add route detailing current user
- Add related certificate products to enrollment API endpoint
- Add admin endpoints to create/update/delete organization/course accesses
- Add admin endpoint to search users
- Add endpoints to get course product relations and courses from organization
- Add `max_validated_orders` field to CourseProductRelation model
- Add api endpoint to retrieve course product relations
- Add `get_selling_organizations` method to Course model
- Add courses client api endpoint
- Add ThumbnailImageField "cover" to Course model
- Add abilities to courses/organizations and their accesses
- Add ID field to the course serializer
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
- Add a nested endpoint to retrieve all the course runs of a course
- Filter courses according to whether they have listed course runs or not

### Changed

- Data returned by product admin serializer
- Refactor the Order FSM to make a better use of transitions
- Allow to get course product relation anonymously
  through a course id / product id pair
- Take products in account to process Course state
- Update OrderSerializer to bind Course information
- Use ThumbnailImageField instead of ImageField for Organization logo
- Refactor how the user is authenticated and passed throughout the request
- Normalize the organization code field
- Activate pagination by default on all endpoints (20 items per page)
- Use user fullname instead of username in order confirmation email
- Rename certificate field into certificate_definition for the ProductSerializer
- Improve certificate serializer
- Upgrade to Django 4.2
- Add model and API endpoint for course wishes
- Change order viewset filter "state" to accept multiple choices.

### Removed

- Remove mypy
- Product API endpoint
- Remove djmoney and Moneyfields
- Badge providers now live in the obc python package
- Remove unused `OrderLiteSerializer`

## [1.2.0] - 2023-08-28

### Changed

- Add languages to the `CourseRun` serializer
- Rename `certificate` field to `certificate_definition`
  into the `ProductSerializer`

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

[unreleased]: https://github.com/openfun/joanie/compare/v1.2.0...main
[1.2.0]: https://github.com/openfun/joanie/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/openfun/joanie/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/openfun/joanie/compare/695965575b80d45c2600a1bcaf84d78bebaec1e7...v1.0.0
