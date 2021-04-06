# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

- Refactor models to allow enrollment without order

[unreleased]: https://github.com/openfun/joanie
