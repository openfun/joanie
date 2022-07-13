# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add the `badges` application
- Add `is_listed` boolean field to course run model
- Add custom actions into admin to generate certificates
- Add a management command to generate certificate for eligible orders
- Add `is_passed` cached property to enrollment model
- Add an api endpoint to retrieve and download certificates
- Add a `get_grades` method to LMSHandler
- Add a computed "state" to Course and CourseRun models
- Add Payplug payment backend and related API routes
- Add Invoice and Transaction models for accounting purposes
- Add credit card model and related api to retrieve, update, delete it
- Serve static files with `whitenoise` third party app
- Add collected static files to the production Docker image
- Install django-money to manage currencies
- Improve course and product admin change views
- Add ngrok to serve Joanie on a public address for development purpose
- Add unique constraint to owner address field to allow only one main address
  per user
- Add fullname field to address model
- Add a web hook endpoint to synchronize course runs from a LMS
- Add a "languages" field to the course run model
- Add stub dependencies required by mypy
- Add .gitlint configuration file
- Use marion and howard to generate certificate for an order
- Use marion and howard to generate invoice for an order
- Implement Address model for billing and add routes API to get, create,
  update and delete address.
- Install security updates in project Docker images
- Enable CORS Headers
- Add routes API to get all products available for a course
  and get or set orders.
- Implement first models to manage courses, products, orders,
  enrollments to course runs and certifications.
- Add a LMSHandler class to select the right LMS Backend to use according to
  the course run's `resource_link` provided
- Add a OpenEdX LMS Backend to manage enrollments

### Changed

- Update codebase to remove the use of deprecated pytz and USE_L10N
  with Django 4.0
- Refactor links between enrollment and order models
- Rename Invoice model into ProformaInvoice
- Update Order serializers to bind certificate
- Order `state` is now a computed property
- Split address fullname field into first_name and last_name fields
- Update CourseSerializer to bind order and enrollment related to the user
- Use a ViewSet to create address api
- Rename the "name" field to "title" (avoid confusion with new "fullname" field)
- Rename "main" field to "is_main" as our naming convention for boolean fields
- Pin base Docker image to `python8-slim-bullseye`
- Make course run dates not required
- Make the "resource_link" field unique and required for course runs
- Normalize course codes and ensure their uniqueness
- Refactor models to allow enrollment without order

[unreleased]: https://github.com/openfun/joanie
