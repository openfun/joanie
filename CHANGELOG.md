# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.9.0] - 2024-10-22

### Added

- Add index on `template` field of the `CertificateDefinition` model
- Add `appendix` field on `ContractDefinition` model
- Allow to edit `appendix` `ContractDefinition` field through the back office

### Changed

- Improve performance of the certificate client API endpoint
- Make payment backend request timeout configurable

## [2.8.0] - 2024-10-16

### Added

- Debit installment on pending order transition if due date is on current day
- Display order credit card detail in the back office
- Send an email reminder to the user when an installment
  will be debited on his credit card on his order's payment schedule
- Send an email to the user when an installment debit has been
  refused
- Send an email to the user when an installment is successfully
  paid
- Support of payment_schedule for certificate products
- Display payment schedule in contract template

### Changed

- Updated `OrderPaymentScheduleDecoder` to return a `date` object for
  the `due_date` attribute and a `Money` object for `amount` attribute
  in the payment_schedule, instead of string values
- Bind payment_schedule into `OrderLightSerializer`
- Generate payment schedule for any kind of product
- Sort credit card list by is_main then descending creation date
- Rework order statuses
- Update the task `debit_pending_installment` to catch up on late
  payments of installments that are in the past
- Deprecated field `has_consent_to_terms` for `Order` model
- Move signature fields before appendices in contract definition template
- Update `handle_notification` signature backend to confirm signature

### Fixed

- Prevent duplicate Address objects for a user or an organization

### Removed

- Remove the `has_consent_to_terms` field from the `Order` edit view
  in the back office application


## [2.7.1] - 2024-10-02

### Fixed

- Downgrade to django-storages 1.14.3

## [2.7.0] - 2024-09-23

### Changed

- Update round robin logic to favor author organizations
- Reassign organization for pending orders

### Fixed

- Improve signature backend `handle_notification` error catching
- Allow to cancel an enrollment order linked to an archived course run

## [2.6.1] - 2024-07-25

### Fixed

- Improve error catching in the `populate_certificate_signatory` command

## [2.6.0] - 2024-07-24

### Added

- Add management command to fix imported certificates without signatory

### Fixed

- Fix signatories retrieval logic in edx certificate import

## [2.5.1] - 2024-06-25

### Fixed

- Fix OpenEdX enrollment mode choice logic

## [2.5.0] - 2024-06-25

### Added

- Add `created_on` column to the `Order` list view in the backoffice

### Changed

- Do not update OpenEdX enrollment if this one is already
  up-to-date on the remote lms

## [2.4.0] - 2024-06-21

### Added

- Add settings configuration for the contract's country calendar to
  manage the payment schedule and the withdrawal period in days

### Changed

- Catch all exceptions raised by enroll_user_to_course_run method

### Fixed

- Fix enrollment mode update on order validation

## [2.3.0] - 2024-06-18

### Added

- Add `payment_provider` attribute to `CreditCard` model
- Allow to tokenize a card endpoint for a user
- Add `state` field to NestedOrderSerializer

### Changed

- Update certificate template to render logo of organization if
  it has a value.
- Add `currency` field to `OrderPaymentSerializer` serializer
- Allow an order with `no_payment` state to pay for failed installment
  on a payment schedule
- Order certificate filter now returns also legacy degree certificates
  linked to an enrollment

### Fixed

- Ensure when API requests fails with payment provider, it raises
  an error for `create_payment`, `create_one_click_payment` and
  `create_zero_click_payment`
- Improve error management of `set_enrollment` method of
  MoodleBackend.
- Bind properly organizations in a certificate template sentence

## [2.2.0] - 2024-05-22

### Added

- Allow to pay failed installment on a payment schedule of an order
- BO : Highlight graded target courses in product detail view
- Add `payment_schedule` property to `OrderSerializer`
- Allow to filter enrollment through `is_active` field on the client API
- Add the possibility to add a syllabus inside the product form
- Add a command to trigger the daily due payments

### Changed

- Complete Lyra payment creation payload

### Fixed

- Lyra backend save card logic
- Manage invalid logging secret key
- Accesses list layout
- Product target course layout
- Update DatePicker with keyboard
- Order view when organization is not defined

## [2.1.0] - 2024-05-02

### Added

- Add accessibility section from Richie course syllabus
  in contract definition template through RDF attributes
- Update signatories for organization owners and student on ongoing
  signature procedures
- Add enrollments pages
- Addition of clickable columns value in the different lists
- Add admin page to decrypt additional data sent to Sentry
- Allow to link a syllabus inside the product detail view
- Add Lyra payment backend
- BO : Add the possibility to add a syllabus inside the course form

### Changed

- Use `NestedGenericViewSet` class for nested routes
  on API viewsets (client and admin)
- Migrate from `django-fsm` to `viewflow.fsm`
- Store certificate images through a new DocumentImage model
- Migrate to Sentry SDK 2.0
- Add required filter by `Organization` and search through
  query on learner for certificate view in django admin
- Migrate from `django-fsm` to `viewflow.fsm`
- Use generic AdminCourseProductRelationSerializer
- Make editing forms in auto save mode
- Format all displayed date to the format "10/14/1983, 1:30 PM"

### Fixed

- Nested Order Course API client viewset returns the orders
  where the user has access to organization
- Contract's context `course_start`, `course_end`, `course_effort`
  and `course_price` are strings for template tags formatting
- Prevent newsletter subscription on user save failure
- Query string search for enrollment in django admin backoffice
- Encrypt sentry additional data (may contain sensitive data)

## [2.0.1] - 2024-04-16

### Fixed

- Ignore conflicts when creating batch of enrollments
- Fix translation content logic

## [2.0.0] - 2024-04-10

### Added

- Add a new endpoint to withdraw an order
- Endpoint to retrieve the first course_run related to a course_link
- Add order payment schedule
- Manage commercial newsletter subscriptions
- Allow backoffice to generate certificates from a course and product relation
- Bind remote catalog syllabus to contract template
- Add redis backend to cache configuration
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

- Update network name in docker-compose file in order  to fit richie
  and openedx-docker naming.
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
- Fix translation content logic

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

[unreleased]: https://github.com/openfun/joanie/compare/v2.9.0...main
[2.9.0]: https://github.com/openfun/joanie/compare/v2.8.0...v2.9.0
[2.8.0]: https://github.com/openfun/joanie/compare/v2.7.1...v2.8.0
[2.7.1]: https://github.com/openfun/joanie/compare/v2.7.0...v2.7.1
[2.7.0]: https://github.com/openfun/joanie/compare/v2.6.1...v2.7.0
[2.6.1]: https://github.com/openfun/joanie/compare/v2.6.0...v2.6.1
[2.6.0]: https://github.com/openfun/joanie/compare/v2.5.1...v2.6.0
[2.5.0]: https://github.com/openfun/joanie/compare/v2.4.0...v2.5.0
[2.4.0]: https://github.com/openfun/joanie/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/openfun/joanie/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/openfun/joanie/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/openfun/joanie/compare/v2.0.1...v2.1.0
[2.0.1]: https://github.com/openfun/joanie/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/openfun/joanie/compare/v1.2.0...v2.0.0
[1.2.0]: https://github.com/openfun/joanie/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/openfun/joanie/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/openfun/joanie/compare/695965575b80d45c2600a1bcaf84d78bebaec1e7...v1.0.0
