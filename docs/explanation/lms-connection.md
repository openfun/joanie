# LMS Connection

Joanie contains a `lms_handler` app which contains all the logic to interact
with your LMS.

## Settings

You can link Joanie to several LMSs. You have to define your LMSs through the `JOANIE_LMS_BACKENDS`
settings which is a list of LMS configuration.

e.g: A basic configuration

```python
JOANIE_LMS_BACKENDS = [
        {
            "BACKEND": values.Value(environ_name="MY_LMS_BACKEND", environ_prefix=None),
            "BASE_URL": values.Value(environ_name="MY_LMS_BASE_URL", environ_prefix=None),
            "SELECTOR_REGEX" : values.Value(environ_name="MY_LMS_SELECTOR_REGEX", environ_prefix=None)
        }
    ]
```

`BACKEND`, `BASE_URL`, `SELECTOR_REGEX` are the three settings required by `LMSHandler`. In fact,
the returned LMS Backend instance has a property `configuration` with all these settings. In this
way, if your LMS Backend implementation requires extra settings like an API Key to make server to
server requests, this is also the right place to define it.

- `BACKEND`: This is the dotted module path of your lms handler backend class. For now, only OpenEdX
  handler has been implemented. They are stored into
  `joanie.lms_handler.backends.[LMS_NAME].[BACKEND_CLASS_NAME]`. (If you need a backend handler for
  another LMS, feel free to [open a issue](https://github.com/openfun/joanie/issues)
  or [contribute with a PR](https://github.com/openfun/joanie/pulls) to Joanie.)
- `BASE_URL`: This is the endpoint from which your LMS is accessible.
- `SELECTOR_REGEX`: To detect which LMS to use, `LMSHandler` has a `select_lms` method which
  iterates over the `LMS_BACKENDS` configuration and checks if the provided endpoint matches the
  `SELECTOR_REGEX`. In most case, a simple regexp that checks the endpoint domain should be enough.

## LMSHandler

The `LMSHandler` class is in charge to select the right backend class to interact with your LMS and
returns an instance.

To detect which handler to use, `LMSHandler` has a `select_lms` method which tries to match the
course run's `resource_link` with the `SELECTOR_REGEX` of each `LMS_BACKENDS` defined in settings.
If there is no match, `None` value is returned. Otherwise it returns an instance of the first
`LMS_BACKEND['BACKEND']` matched then you can use this backend to make action.

Moreover, a `get_all_lms` method is also available to retrieve a list of all LMS Backend. In this
way, you are able to apply same kind of operation on all of your connected LMS at once. Of course,
it requires that your LMS backend implementations are normalized.

## Actions

### Manage enrollments

- `get_enrollment(username, resource_link)`

  Retrieve user enrollment information about a course run.

- `set_enrollment(username, resource_link, active=True)`

  Un/Enroll an user to a course run.
