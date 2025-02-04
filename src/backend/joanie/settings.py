"""
Django settings for Joanie project.

Generated by 'django-admin startproject' using Django 3.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

import json
import os

from django.utils.translation import gettext_lazy as _

import sentry_sdk
from configurations import Configuration, values
from sentry_sdk.integrations.django import DjangoIntegration

from joanie.core.utils import JSONValue, LMSBackendsValue
from joanie.core.utils.sentry import before_send

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join("/", "data")


def get_release():
    """
    Get the current release of the application

    By release, we mean the release from the version.json file à la Mozilla [1]
    (if any). If this file has not been found, it defaults to "NA".

    [1]
    https://github.com/mozilla-services/Dockerflow/blob/master/docs/version_object.md
    """
    # Try to get the current release from the version.json file generated by the
    # CI during the Docker image build
    try:
        with open(os.path.join(BASE_DIR, "version.json"), encoding="utf8") as version:
            return json.load(version)["version"]
    except FileNotFoundError:
        return "NA"  # Default: not available


class Base(Configuration):
    """
    This is the base configuration every configuration (aka environnement) should inherit from. It
    is recommended to configure third-party applications by creating a configuration mixins in
    ./configurations and compose the Base configuration with those mixins.

    It depends on an environment variable that SHOULD be defined:

    * DJANGO_SECRET_KEY

    You may also want to override default configuration by setting the following environment
    variables:

    * DJANGO_SENTRY_DSN
    * DB_NAME
    * DB_HOST
    * DB_PASSWORD
    * DB_USER
    """

    DEBUG = False
    USE_SWAGGER = False

    API_VERSION = "v1.0"

    # Security
    ALLOWED_HOSTS = values.ListValue([])
    SECRET_KEY = values.Value(None)
    LOGGING_SECRET_KEY = values.Value(None)
    # Security - Server to server authorized API keys
    JOANIE_AUTHORIZED_API_TOKENS = values.ListValue([], environ_prefix=None)

    # Application definition
    ROOT_URLCONF = "joanie.urls"
    WSGI_APPLICATION = "joanie.wsgi.application"

    # Database
    DATABASES = {
        "default": {
            "ENGINE": values.Value(
                "django.db.backends.postgresql_psycopg2",
                environ_name="DB_ENGINE",
                environ_prefix=None,
            ),
            "NAME": values.Value("joanie", environ_name="DB_NAME", environ_prefix=None),
            "USER": values.Value("fun", environ_name="DB_USER", environ_prefix=None),
            "PASSWORD": values.Value(
                "pass", environ_name="DB_PASSWORD", environ_prefix=None
            ),
            "HOST": values.Value(
                "localhost", environ_name="DB_HOST", environ_prefix=None
            ),
            "PORT": values.Value(5432, environ_name="DB_PORT", environ_prefix=None),
        }
    }
    DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

    # Static files (CSS, JavaScript, Images)
    STATIC_URL = "/static/"
    STATIC_ROOT = os.path.join(DATA_DIR, "static")
    MEDIA_URL = "/media/"
    MEDIA_ROOT = os.path.join(DATA_DIR, "media")

    SITE_ID = 1

    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
        "contracts": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {
                "location": os.path.join(DATA_DIR, "contracts"),
                "base_url": "/contracts/",
            },
        },
    }

    # Internationalization
    # https://docs.djangoproject.com/en/3.1/topics/i18n/

    # Languages
    LANGUAGE_CODE = values.Value("en-us")
    JOANIE_DEFAULT_COUNTRY_CODE = values.Value("FR", environ_prefix=None)

    DRF_NESTED_MULTIPART_PARSER = {
        # output of parser is converted to querydict
        # if is set to False, dict python is returned
        "querydict": False,
    }

    # Careful! Languages should be ordered by priority, as this tuple is used to get
    # fallback/default languages throughout the app.
    LANGUAGES = values.SingleNestedTupleValue(
        (
            ("en-us", _("English")),
            ("fr-fr", _("French")),
        )
    )

    LOCALE_PATHS = (os.path.join(BASE_DIR, "locale"),)

    TIME_ZONE = "UTC"
    USE_I18N = True
    USE_TZ = True

    # Templates
    TEMPLATES = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [os.path.join(BASE_DIR, "templates")],
            "OPTIONS": {
                "context_processors": [
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                    "django.template.context_processors.csrf",
                    "django.template.context_processors.debug",
                    "django.template.context_processors.i18n",
                    "django.template.context_processors.media",
                    "django.template.context_processors.request",
                    "django.template.context_processors.tz",
                    "joanie.core.context_processors.admin.settings_processors",
                ],
                "loaders": [
                    "django.template.loaders.filesystem.Loader",
                    "django.template.loaders.app_directories.Loader",
                ],
            },
        },
    ]

    MIDDLEWARE = [
        "django.middleware.security.SecurityMiddleware",
        "whitenoise.middleware.WhiteNoiseMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.locale.LocaleMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
        "corsheaders.middleware.CorsMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "joanie.core.middleware.JoanieDockerflowMiddleware",
    ]

    AUTHENTICATION_BACKENDS = [
        "django.contrib.auth.backends.ModelBackend",
    ]

    # Django applications from the highest priority to the lowest
    INSTALLED_APPS = [
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.sites",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        "django.contrib.humanize",
        # Third party apps
        "admin_auto_filters",
        "django_object_actions",
        "adminsortable2",
        "corsheaders",
        "dockerflow.django",
        "django_filters",
        "rest_framework",
        "parler",
        "easy_thumbnails",
        # Joanie
        "joanie.core",
        # contrib admin needs to be after joanie.core to override templates
        "django.contrib.admin",
        "joanie.payment",
        "joanie.badges",
        "joanie.demo",
        "joanie.edx_imports",
        "joanie.signature",
        "drf_spectacular",
    ]

    # Joanie
    JOANIE_LMS_BACKENDS = LMSBackendsValue([], environ_prefix=None)
    JOANIE_COURSE_RUN_SYNC_SECRETS = values.ListValue([], environ_prefix=None)
    MOODLE_AUTH_METHOD = values.Value(
        "oauth2", environ_name="MOODLE_AUTH_METHOD", environ_prefix=None
    )
    JOANIE_BADGE_PROVIDERS = {
        "obf": {
            "client_id": values.Value(
                environ_name="OBF_CLIENT_ID", environ_prefix=None
            ),
            "client_secret": values.Value(
                environ_name="OBF_CLIENT_SECRET", environ_prefix=None
            ),
        }
    }

    JOANIE_BACKOFFICE_BASE_URL = values.Value(
        environ_name="JOANIE_BACKOFFICE_BASE_URL",
        environ_prefix=None,
    )

    JOANIE_CATALOG_BASE_URL = values.Value(
        environ_name="JOANIE_CATALOG_BASE_URL",
        environ_prefix=None,
    )

    JOANIE_CATALOG_NAME = values.Value(
        environ_name="JOANIE_CATALOG_NAME",
        environ_prefix=None,
    )

    # Context processors for document issuers
    JOANIE_DOCUMENT_ISSUER_CONTEXT_PROCESSORS = {
        "contract_definition": values.ListValue(
            [],
            environ_name="JOANIE_CONTRACT_CONTEXT_PROCESSORS",
            environ_prefix=None,
        ),
    }

    # Cache
    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    }

    JOANIE_SERIALIZER_DEFAULT_CACHE_TTL = values.PositiveIntegerValue(
        3600, environ_prefix=None
    )  # 1 hour
    JOANIE_ENROLLMENT_GRADE_CACHE_TTL = values.PositiveIntegerValue(
        600, environ_prefix=None
    )  # 10 minutes

    REST_FRAMEWORK = {
        "DEFAULT_AUTHENTICATION_CLASSES": (
            "joanie.core.authentication.DelegatedJWTAuthentication",
        ),
        "DEFAULT_FILTER_BACKENDS": [
            "django_filters.rest_framework.DjangoFilterBackend"
        ],
        "DEFAULT_PARSER_CLASSES": [
            "rest_framework.parsers.JSONParser",
            "nested_multipart_parser.drf.DrfNestedParser",
        ],
        "EXCEPTION_HANDLER": "joanie.core.api.exception_handler",
        "DEFAULT_PAGINATION_CLASS": "joanie.core.pagination.Pagination",
        "PAGE_SIZE": 20,
        "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
        "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    }

    SPECTACULAR_SETTINGS = {
        "TITLE": "Joanie API",
        "DESCRIPTION": "This is the Joanie API schema.",
        "VERSION": "2.0.0",
        "SERVE_INCLUDE_SCHEMA": False,
        "ENABLE_DJANGO_DEPLOY_CHECK": values.BooleanValue(
            default=False,
            environ_name="SPECTACULAR_SETTINGS_ENABLE_DJANGO_DEPLOY_CHECK",
        ),
        "ENUM_NAME_OVERRIDES": {
            "EnrollmentStateEnum": "joanie.core.enums.ENROLLMENT_STATE_CHOICES",
            "OrderStateEnum": "joanie.core.enums.ORDER_STATE_CHOICES",
            "OrganizationAccessRoleChoiceEnum": (
                "joanie.core.models.OrganizationAccess.ROLE_CHOICES"
            ),
            "CourseAccessRoleChoiceEnum": "joanie.core.models.CourseAccess.ROLE_CHOICES",
        },
        "COMPONENT_SPLIT_REQUEST": True,
        # OTHER SETTINGS
        "SWAGGER_UI_DIST": "SIDECAR",  # shorthand to use the sidecar instead
        "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
        "REDOC_DIST": "SIDECAR",
    }

    SIMPLE_JWT = {
        "ALGORITHM": values.Value("HS256", environ_name="JWT_ALGORITHM"),
        "SIGNING_KEY": values.SecretValue(
            environ_name="JWT_PRIVATE_SIGNING_KEY",
        ),
        "AUTH_HEADER_TYPES": ("Bearer",),
        "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
        "USER_ID_FIELD": "username",
        "USER_ID_CLAIM": "username",
        "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    }
    JWT_USER_FIELDS_SYNC = values.DictValue(
        {
            "email": "email",
            "first_name": "full_name",
            "language": "language",
            "has_subscribed_to_commercial_newsletter": "has_subscribed_to_commercial_newsletter",
        },
        environ_name="JOANIE_JWT_USER_FIELDS_SYNC",
        environ_prefix=None,
    )

    # Mail
    EMAIL_BACKEND = values.Value("django.core.mail.backends.smtp.EmailBackend")
    EMAIL_HOST = values.Value(None)
    EMAIL_HOST_USER = values.Value(None)
    EMAIL_HOST_PASSWORD = values.Value(None)
    EMAIL_PORT = values.PositiveIntegerValue(None)
    EMAIL_USE_TLS = values.BooleanValue(False)
    EMAIL_FROM = values.Value("from@fun-mooc.fr")

    # Django Money
    DEFAULT_CURRENCY = "EUR"
    CURRENCIES = (DEFAULT_CURRENCY,)

    # Joanie settings
    JOANIE_VAT = values.Value(20, environ_name="JOANIE_VAT", environ_prefix=None)
    JOANIE_INVOICE_SELLER_ADDRESS = values.Value(
        """France Université Numérique
        10 Rue Stine,
        75001 Paris, FR""",
        environ_name="JOANIE_INVOICE_SELLER_ADDRESS",
        environ_prefix=None,
    )
    JOANIE_INVOICE_COMPANY_CONTEXT = values.Value(
        """10 rue Stine, 75001 Paris
        RCS Paris XXX XXX XXX - SIRET XXX XXX XXX XXXXX - APE XXXXX
        VAT Number XXXXXXXXX""",
        environ_name="JOANIE_INVOICE_COMPANY_CONTEXT",
        environ_prefix=None,
    )

    AUTH_USER_MODEL = "core.User"

    # Payment
    JOANIE_PAYMENT_BACKEND = {
        "backend": values.Value(
            environ_name="JOANIE_PAYMENT_BACKEND",
            environ_prefix=None,
        ),
        "timeout": values.PositiveIntegerValue(
            5, environ_name="JOANIE_PAYMENT_TIMEOUT", environ_prefix=None
        ),
        # Check the docstring of the related payment backend to know
        # which dict to pass here.
        "configuration": values.DictValue(
            environ_name="JOANIE_PAYMENT_CONFIGURATION", environ_prefix=None
        ),
    }
    JOANIE_PAYMENT_SCHEDULE_LIMITS = values.DictValue(
        {150: (100,), 200: (30, 70), 500: (30, 35, 35), 1000: (30, 25, 25, 20)},
        environ_name="JOANIE_PAYMENT_SCHEDULE_LIMITS",
        environ_prefix=None,
    )
    # The full list of countries available for use:
    # https://github.com/workalendar/workalendar#available-calendars
    JOANIE_CALENDAR = values.Value(
        "workalendar.europe.France",
        environ_name="JOANIE_CALENDAR",
        environ_prefix=None,
    )
    # Number of days for the withdrawal period as required by your country's contract legislation
    JOANIE_WITHDRAWAL_PERIOD_DAYS = values.PositiveIntegerValue(
        16,
        environ_name="JOANIE_WITHDRAWAL_PERIOD_DAYS",
        environ_prefix=None,
    )
    # Email for installment payment
    # Add here the dashboard link of orders
    JOANIE_DASHBOARD_ORDER_LINK = values.Value(
        None,
        environ_name="JOANIE_DASHBOARD_ORDER_LINK",
        environ_prefix=None,
    )
    # Add here the number of days ahead before notifying a user
    # on his next installment debit
    JOANIE_INSTALLMENT_REMINDER_PERIOD_DAYS = values.Value(
        2,
        environ_name="JOANIE_INSTALLMENT_REMINDER_DAYS_BEFORE",
        environ_prefix=None,
    )
    # Link to the microcertification terms of service which is used
    # at a first place in the Unicamp certificate template
    JOANIE_DEGREE_MICROCERTIFICATION_TERMS_URL = values.Value(
        None,
        environ_name="JOANIE_DEGREE_MICROCERTIFICATION_TERMS_URL",
        environ_prefix=None,
    )

    # Minimum time authorized for order latest updates when the order are
    # in the state `to_sign` or `signing`. It's also applied for order's of
    # product type certificate that are in state `to_save_payment_method`
    JOANIE_ORDER_UPDATE_DELAY_LIMIT_IN_SECONDS = values.Value(
        60 * 60,  # 1 hour
        environ_name="JOANIE_ORDER_UPDATE_DELAY_LIMIT_IN_SECONDS",
        environ_prefix=None,
    )

    # CORS
    CORS_ALLOW_CREDENTIALS = True
    CORS_ALLOW_ALL_ORIGINS = values.BooleanValue(False)
    CORS_ALLOWED_ORIGINS = values.ListValue([])
    CORS_ALLOWED_ORIGIN_REGEXES = values.ListValue([])

    # Sentry
    SENTRY_DSN = values.Value(None, environ_name="SENTRY_DSN")

    # Richie's synchronization
    # COURSE_WEB_HOOKS environment variable should be a stringified JSON array of
    # objects with the following structure:
    # e.g:
    # DJANGO_COURSE_WEB_HOOKS=[{"url": "http://example.com", "secret": "secret", "verify": true}]
    COURSE_WEB_HOOKS = JSONValue([])

    JOANIE_ACTIVITY_LOG_SECRETS = values.ListValue(
        [],
        environ_name="JOANIE_ACTIVITY_LOG_SECRETS",
        environ_prefix=None,
    )

    # Easy thumbnails
    THUMBNAIL_EXTENSION = "webp"
    THUMBNAIL_TRANSPARENCY_EXTENSION = "webp"
    THUMBNAIL_ALIASES = {
        "core.Course.cover": {
            "1920w": {"size": (1920, 1080), "crop": "scale", "upscale": True},
            "1280w": {"size": (1280, 720), "crop": "scale", "upscale": True},
            "768w": {"size": (768, 432), "crop": "scale", "upscale": True},
            "384w": {"size": (384, 216), "crop": "scale", "upscale": True},
        },
        "core.Organization.logo": {
            "1024w": {"size": (1024, 1024), "crop": "scale", "upscale": True},
            "512w": {"size": (512, 512), "crop": "scale", "upscale": True},
            "256w": {"size": (256, 256), "crop": "scale", "upscale": True},
            "128w": {"size": (128, 128), "crop": "scale", "upscale": True},
        },
    }
    THUMBNAIL_STORAGE_S3_LOCATION = values.Value("thumbnails")

    # Signature Backend
    JOANIE_SIGNATURE_BACKEND = values.Value(
        "joanie.signature.backends.dummy.DummySignatureBackend",
        environ_name="JOANIE_SIGNATURE_BACKEND",
        environ_prefix=None,
    )
    JOANIE_SIGNATURE_VALIDITY_PERIOD_IN_SECONDS = values.PositiveIntegerValue(
        99 * 60 * 60 * 24,  # Duration in seconds
        # 99 days is the maximum validity period accepted by Lex Persona
        environ_name="JOANIE_SIGNATURE_VALIDITY_PERIOD_IN_SECONDS",
        environ_prefix=None,
    )

    JOANIE_SIGNATURE_TIMEOUT = values.PositiveIntegerValue(
        3, environ_name="JOANIE_SIGNATURE_TIMEOUT", environ_prefix=None
    )

    # Signature Backend - Lex Persona
    JOANIE_SIGNATURE_LEXPERSONA_BASE_URL = values.Value(
        None, environ_name="JOANIE_SIGNATURE_LEXPERSONA_BASE_URL", environ_prefix=None
    )
    JOANIE_SIGNATURE_LEXPERSONA_CONSENT_PAGE_ID = values.Value(
        None,
        environ_name="JOANIE_SIGNATURE_LEXPERSONA_CONSENT_PAGE_ID",
        environ_prefix=None,
    )
    JOANIE_SIGNATURE_LEXPERSONA_SESSION_USER_ID = values.Value(
        None,
        environ_name="JOANIE_SIGNATURE_LEXPERSONA_SESSION_USER_ID",
        environ_prefix=None,
    )
    JOANIE_SIGNATURE_LEXPERSONA_PROFILE_ID = values.Value(
        None, environ_name="JOANIE_SIGNATURE_LEXPERSONA_PROFILE_ID", environ_prefix=None
    )
    JOANIE_SIGNATURE_LEXPERSONA_TOKEN = values.Value(
        None, environ_name="JOANIE_SIGNATURE_LEXPERSONA_TOKEN", environ_prefix=None
    )

    # Celery
    CELERY_BROKER_URL = values.Value("redis://redis:6379/0")
    CELERY_BROKER_TRANSPORT_OPTIONS = values.DictValue({})
    CELERY_DEFAULT_QUEUE = values.Value("celery")

    # Newsletters
    BREVO_API_URL = values.Value(
        "https://api.brevo.com/v3/", environ_name="BREVO_API_URL", environ_prefix=None
    )
    BREVO_API_KEY = values.Value(
        None, environ_name="BREVO_API_KEY", environ_prefix=None
    )
    BREVO_COMMERCIAL_NEWSLETTER_LIST_ID = values.IntegerValue(
        None, environ_name="BREVO_COMMERCIAL_NEWSLETTER_LIST_ID", environ_prefix=None
    )
    BREVO_WEBHOOK_TOKEN = values.Value(
        None, environ_name="BREVO_WEBHOOK_TOKEN", environ_prefix=None
    )

    # Open edX database import
    EDX_DOMAIN = values.Value(None, environ_name="EDX_DOMAIN", environ_prefix=None)
    EDX_DATABASE_HOST = values.Value(
        None, environ_name="EDX_DATABASE_HOST", environ_prefix=None
    )
    EDX_DATABASE_NAME = values.Value(
        None, environ_name="EDX_DATABASE_NAME", environ_prefix=None
    )
    EDX_DATABASE_USER = values.Value(
        None, environ_name="EDX_DATABASE_USER", environ_prefix=None
    )
    EDX_DATABASE_PASSWORD = values.Value(
        None, environ_name="EDX_DATABASE_PASSWORD", environ_prefix=None
    )
    EDX_DATABASE_PORT = values.IntegerValue(
        None, environ_name="EDX_DATABASE_PORT", environ_prefix=None
    )
    EDX_DATABASE_DEBUG = values.BooleanValue(
        False, environ_name="EDX_DATABASE_DEBUG", environ_prefix=None
    )

    EDX_MONGODB_HOST = values.Value(
        None, environ_name="EDX_MONGODB_HOST", environ_prefix=None
    )
    EDX_MONGODB_PORT = values.IntegerValue(
        None, environ_name="EDX_MONGODB_PORT", environ_prefix=None
    )
    EDX_MONGODB_USER = values.Value(
        None, environ_name="EDX_MONGODB_USER", environ_prefix=None
    )
    EDX_MONGODB_PASSWORD = values.Value(
        None, environ_name="EDX_MONGODB_PASSWORD", environ_prefix=None
    )
    EDX_MONGODB_NAME = values.Value(
        None, environ_name="EDX_MONGODB_NAME", environ_prefix=None
    )
    EDX_MONGODB_READPREFERENCE = values.Value(
        "secondaryPreferred",
        environ_name="EDX_MONGODB_READPREFERENCE",
        environ_prefix=None,
    )
    EDX_MONGODB_REPLICASET = values.Value(
        None, environ_name="EDX_MONGODB_REPLICASET", environ_prefix=None
    )

    EDX_TIME_ZONE = values.Value(
        None, environ_name="EDX_TIME_ZONE", environ_prefix=None
    )
    EDX_SECRET = values.Value(None, environ_name="EDX_SECRET", environ_prefix=None)

    # pylint: disable=invalid-name
    @property
    def ENVIRONMENT(self):
        """Environment in which the application is launched."""
        return self.__class__.__name__.lower()

    # pylint: disable=invalid-name
    @property
    def RELEASE(self):
        """
        Return the release information.

        Delegate to the module function to enable easier testing.
        """
        return get_release()

    # pylint: disable=invalid-name
    @property
    def PARLER_LANGUAGES(self):
        """
        Return languages for Parler computed from the LANGUAGES and LANGUAGE_CODE settings.
        """
        return {
            self.SITE_ID: tuple({"code": code} for code, _name in self.LANGUAGES),
            "default": {
                "fallbacks": [self.LANGUAGE_CODE],
                "hide_untranslated": False,
            },
        }

    @classmethod
    def post_setup(cls):
        """Post setup configuration.
        This is the place where you can configure settings that require other
        settings to be loaded.
        """
        super().post_setup()

        # The SENTRY_DSN setting should be available to activate sentry for an environment
        if cls.SENTRY_DSN is not None:
            sentry_sdk.init(
                dsn=cls.SENTRY_DSN,
                environment=cls.__name__.lower(),
                release=get_release(),
                integrations=[DjangoIntegration()],
                before_send=before_send,
            )
            sentry_sdk.set_tag("application", "backend")

        if cls.BREVO_WEBHOOK_TOKEN is not None:
            cls.JOANIE_AUTHORIZED_API_TOKENS.append(cls.BREVO_WEBHOOK_TOKEN)  # pylint: disable=no-member


class Build(Base):
    """Settings used when the application is built.

    This environment should not be used to run the application. Just to build it with non-blocking
    settings.
    """

    SECRET_KEY = values.Value("DummyKey")
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": values.Value(
                "whitenoise.storage.CompressedManifestStaticFilesStorage",
                environ_name="STORAGES_STATICFILES_BACKEND",
            ),
        },
    }


class Development(Base):
    """
    Development environment settings

    We set DEBUG to True and configure the server to respond from all hosts.
    """

    ALLOWED_HOSTS = ["*"]
    CORS_ALLOW_ALL_ORIGINS = True
    JOANIE_URL = values.Value(
        "http://localhost:8072", environ_name="LOCALTUNNEL_URL", environ_prefix=None
    )
    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:3000",
        JOANIE_URL,
        Base.JOANIE_BACKOFFICE_BASE_URL,
    ]
    DEBUG = True
    DEVELOPER_EMAIL = values.Value(
        "developer@example.com",
        environ_name="DEVELOPER_EMAIL",
        environ_prefix=None,
    )

    LOGGING = values.DictValue(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                },
            },
            "loggers": {
                "joanie": {
                    "handlers": ["console"],
                    "level": "WARNING",
                },
                "request.summary": {
                    "handlers": ["console"],
                    "level": "WARNING",
                },
            },
        }
    )

    SESSION_COOKIE_NAME = "joanie_sessionid"

    LOGIN_URL = "/admin/login/"
    LOGOUT_URL = "/admin/logout/"

    USE_SWAGGER = True

    def __init__(self):
        # pylint: disable=invalid-name
        self.INSTALLED_APPS += [
            "django_extensions",
            "drf_spectacular_sidecar",
            "joanie.debug",
        ]


class Test(Base):
    """Test environment settings"""

    JOANIE_LMS_BACKENDS = [
        {
            "API_TOKEN": "FakeEdXAPIKey",
            "BACKEND": "joanie.lms_handler.backends.dummy.DummyLMSBackend",
            "BASE_URL": "http://localhost:8073",
            "SELECTOR_REGEX": r"^(?P<course_id>.*)$",
            "COURSE_REGEX": r"^(?P<course_id>.*)$",
        }
    ]

    JOANIE_PAYMENT_BACKEND = {
        "backend": "joanie.payment.backends.dummy.DummyPaymentBackend",
        "timeout": 5,
    }

    JOANIE_SIGNATURE_BACKEND = "joanie.signature.backends.dummy.DummySignatureBackend"

    JOANIE_ENROLLMENT_GRADE_CACHE_TTL = 0
    JOANIE_DOCUMENT_ISSUER_CONTEXT_PROCESSORS = {"contract_definition": []}

    JOANIE_PAYMENT_SCHEDULE_LIMITS = values.DictValue(
        {0: (30, 70)},
        environ_name="JOANIE_PAYMENT_SCHEDULE_LIMITS",
        environ_prefix=None,
    )

    JOANIE_DASHBOARD_ORDER_LINK = (
        "http://localhost:8070/dashboard/courses/orders/:orderId/"
    )

    JOANIE_DEGREE_MICROCERTIFICATION_TERMS_URL = "https://example.com/terms"

    LOGGING = values.DictValue(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                },
            },
            "loggers": {
                "joanie": {
                    "handlers": ["console"],
                    "level": "WARNING",
                },
                "request.summary": {
                    "handlers": ["console"],
                    "level": "WARNING",
                },
            },
        }
    )
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]
    USE_SWAGGER = True
    DEVELOPER_EMAIL = "developer@example.com"

    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
        "contracts": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
            "OPTIONS": {
                "location": os.path.join(DATA_DIR, "contracts"),
                "base_url": "/contracts/",
            },
        },
    }

    CELERY_TASK_ALWAYS_EAGER = values.BooleanValue(True)

    def __init__(self):
        # pylint: disable=invalid-name
        self.INSTALLED_APPS += [
            "joanie.tests",
            "drf_spectacular_sidecar",
            "joanie.debug",
        ]


class ContinuousIntegration(Test):
    """
    Continuous Integration environment settings

    nota bene: it should inherit from the Test environment.
    """


class Production(Base):
    """
    Production environment settings

    You must define the ALLOWED_HOSTS environment variable in Production
    configuration (and derived configurations):
    ALLOWED_HOSTS=["foo.com", "foo.fr"]
    """

    # Security
    ALLOWED_HOSTS = values.ListValue(None)
    CSRF_TRUSTED_ORIGINS = values.ListValue([])
    CSRF_COOKIE_DOMAIN = values.Value(None)
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # SECURE_PROXY_SSL_HEADER allows to fix the scheme in Django's HttpRequest
    # object when your application is behind a reverse proxy.
    #
    # Keep this SECURE_PROXY_SSL_HEADER configuration only if :
    # - your Django app is behind a proxy.
    # - your proxy strips the X-Forwarded-Proto header from all incoming requests
    # - Your proxy sets the X-Forwarded-Proto header and sends it to Django
    #
    # In other cases, you should comment the following line to avoid security issues.
    # SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    # Modern browsers require to have the `secure` attribute on cookies with `Samesite=none`
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

    # For static files in production, we want to use a backend that includes a hash in
    # the filename, that is calculated from the file content, so that browsers always
    # get the updated version of each file.
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
        },
        "staticfiles": {
            # For static files in production, we want to use a backend that includes a hash in
            # the filename, that is calculated from the file content, so that browsers always
            # get the updated version of each file.
            "BACKEND": values.Value(
                "whitenoise.storage.CompressedManifestStaticFilesStorage",
                environ_name="STORAGES_STATICFILES_BACKEND",
            )
        },
        "contracts": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": values.Value(
                    "tf-default-joanie-contracts-storage",
                    environ_name="CONTRACTS_AWS_STORAGE_BUCKET_NAME",
                ),
                "location": "contracts",
            },
        },
    }

    # Cache
    # Enable the alternate connection factory.
    DJANGO_REDIS_CONNECTION_FACTORY = values.Value(
        "django_redis.pool.ConnectionFactory",
        environ_prefix=None,
        environ_name="DJANGO_REDIS_CONNECTION_FACTORY",
    )

    CACHES = {
        "default": {
            "BACKEND": values.Value(
                "django_redis.cache.RedisCache", environ_name="CACHE_DEFAULT_BACKEND"
            ),
            # The hostname in LOCATION
            "LOCATION": values.Value(
                "redis://redis/0", environ_name="CACHE_DEFAULT_LOCATION"
            ),
            "OPTIONS": values.DictValue(
                {
                    "CLIENT_CLASS": "django_redis.client.DefaultClient",
                },
                environ_name="CACHE_DEFAULT_OPTIONS",
            ),
        },
    }

    THUMBNAIL_DEFAULT_STORAGE = values.Value(
        "joanie.core.storages.JoanieEasyThumbnailS3Storage"
    )

    # Privacy
    SECURE_REFERRER_POLICY = "same-origin"

    # Media
    AWS_S3_ENDPOINT_URL = values.Value()
    AWS_S3_ACCESS_KEY_ID = values.Value()
    AWS_S3_SECRET_ACCESS_KEY = values.Value()
    AWS_STORAGE_BUCKET_NAME = values.Value("tf-default-joanie-media-storage")
    AWS_S3_REGION_NAME = values.Value()


class Feature(Production):
    """
    Feature environment settings

    nota bene: it should inherit from the Production environment.
    """


class Staging(Production):
    """
    Staging environment settings

    nota bene: it should inherit from the Production environment.
    """


class PreProduction(Production):
    """
    Pre-production environment settings

    nota bene: it should inherit from the Production environment.
    """
