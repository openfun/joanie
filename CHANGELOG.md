# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
