# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add routes API to get all products available for a course
  and get or set orders.
- Implement first models to manage course products, orders,
  enrollments to course runs and certifications.
- Add a LMSHandler class to select the right LMS Backend to use according to
  the course run's `resource_link` provided
- Add a OpenEdX LMS Backend to manage enrollments

[unreleased]: https://github.com/openfun/joanie
