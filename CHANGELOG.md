# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[unreleased]: https://github.com/openfun/joanie/compare/v1.0.0...master
[1.0.0]: https://github.com/openfun/joanie/compare/695965575b80d45c2600a1bcaf84d78bebaec1e7...v1.0.0
