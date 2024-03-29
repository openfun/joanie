# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## Added

- Add generate certificate button in Back Office
- Add admin Enrollment endpoint
- Add tabs layout on back offices forms
- Filter admin resources list through their pk
- Allow backoffice to generate certificate if order is eligible
- Allow backoffice admin user to cancel an order
- Add filter tag `iso8601_to_date`
- Allow student to download his owned contract once fully signed
- Allow to filter course product relation by organization title or
  product title or by course code on the client API.
- Allow to filter courses by course code or title on the client API
- Allow to filter orders by product title on the client API
- Allow to filter enrollments by course title on the client API
- Debug app to preview template (certificate, degree, invoice,
  contract definition)
- Allow to filter out organization through course product relation id on
  the client API
- Add custom template tag to convert ISO 8601 duration to a specified time unit.
- Add custom serializer field for duration field to format ISO 8601
- Add effort duration field for the Course Model
- Add phone number field for the User Model
- Add property `verification_uri` to `Certificate` model
- Add a certificate verification view
- Add `has_consent_terms` boolean field to `Order` model
- Bind terms and conditions to the contract definition template
- Extend Site model to store terms and conditions
- Add `join_and` and `list_key` template tags
- Add address and new properties on client OrganizationSerializer
- Add admin endpoints to create/update/delete organization addresses
- Add several admin api endpoint filters
- Filter course product relation client api endpoint by product type
- Link Organization to Address Model
- New properties on Organization model to complete contract definition context
- Allow to bulk sign contracts by training
- Filtering orders by organization, product, and course product relation
- Allow to set CSRF_COOKIE_DOMAIN through env vars
- Dedicated storage for easy_thumbnail using boto3
- Allow to override settings in tray
- Add API endpoints for other services to fetch  data on course run
- Allow to filter contracts by signature state,
  product, course and organization, id and course product relation id
- Add bulk download of signed contracts to generate ZIP archive with command
- Add read-only api admin endpoint to list/retrieve orders
- Add a management command to synchronize course run or product
  on a remote catalog
- Install and configure celery with redis
- Add CachedModelSerializer
- Allow to leave organization empty while order is in draft
- Add API client signature provider to sign contract from an order
- Add admin route to add and modify OrderGroups
- Allow to filter contracts through their signature state
- Allow filtering orders by state or product type exclusion
- Allow filtering orders by enrollment
- Create missing courses automatically on course run sync
- Create `certificate` template
- Add contract and contract definition models with related API endpoints
- Add `instructions` markdown field to `Product` model
- Add filter course by product type
- Enroll as "verified" mode in OpenEdX when enrolling via an order
- Add mermaid graph for Order workflow
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
- Add related certificate products and orders to enrollment API endpoint
- Add admin endpoints to create/update/delete organization/course accesses
- Add admin endpoint to search users
- Add endpoints to get course product relations and courses from organization
- Add order groups to allow limiting the number of seats on a product course
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
- Add some objects to demo-dev command. A credit card, a billing address and
  one order of each state. Also add some order target courses.
- Add markdown editor inside the BO
- Add admin endpoint to manage course product relations
- Add organization contract signature
- Add moodle LMS backend
- Make the target course card title clickable
- Add contract details inside order view
- Add playwright component stack

### Changed

- Update the certificate viewset for the API client to return
  certificates from orders and from enrollments owned by a user.
- Update demo-dev command to add a second product purchase with learner
  signature.
- Improve `degree` certificate template
- Bind organization course author into certificate context
  instead of organization order
- Prevent to create an order with course run that has ended
- Debug view for Certificate, Degree, Contract Definition and Invoice
- Internalize invoice template
- Use HTTPStatus instead of raw HTTP code value
- If a product has a contract, delay auto enroll logic on leaner signature
- Prevent to enroll to not listed course runs related to an order awaiting
  signature of a contract by the learner
- Use Invoice.recipient_address to populate Contract address context
- Link Invoice to Address object
- Update psycopg to version 3
- Update contract api endpoint to retrieve contracts by ownership
- Internalize degree template
- Allow to download enrollment certificate from related download api endpoint
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
- Product and Order serializers now return Contract and ContractDefinition
  object instead of ids.
- Rename nested order serializer attributes to be more descriptive
- Update nested order serializer to return enrollment
- Update order serializer to return enrollment
- Rename serializers attributes to be more descriptive:
  - EnrollmentSerializer
  - OrderSerializer
  - OrderLightSerializer
  - CourseSerializer
  - CourseAccessSerializer
  - OrganizationAccessSerializer
- Rename query parameters to be more descriptive:
  - OrderViewSetFilter
  - ProductViewSetFilter
  - EnrollmentViewSetFilter
- Update admin course serializer to return course runs
- Allow group order deletion through course product relation
- Delete group orders when deleting a course product relation
- Rename admin api payload parameters to be more descriptive:
  - AdminOrganizationAccessSerializer
  - AdminCourseAccessSerializer
  - AdminCourseSerializer
  - AdminCourseRunSerializer
- Update the course runs list
  - delete the resource link column and move it to the options
  - format start and end date
  - add course code colum
- Add an order cancellation action in the order detail view
- Preserve query params filters on page refresh


### Removed

- Remove mypy
- Product API endpoint
- Remove djmoney and Moneyfields
- Badge providers now live in the obc python package
- Remove unused `OrderLiteSerializer`

### Fixed

- Fix unenrollment issue on closed course runs
- Fix auto enrollment with closed and specific course runs
- Fix demo-dev command synchronization error.
- Add missing django dockerflow middleware

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
