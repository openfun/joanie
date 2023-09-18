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

from .core.utils import JSONValue

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

    # Security
    ALLOWED_HOSTS = values.ListValue([])
    SECRET_KEY = values.Value(None)

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

    # Internationalization
    # https://docs.djangoproject.com/en/3.1/topics/i18n/

    # Languages
    LANGUAGE_CODE = values.Value("en-us")

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
    ]

    AUTHENTICATION_BACKENDS = [
        "django.contrib.auth.backends.ModelBackend",
    ]

    # Django applications from the highest priority to the lowest
    INSTALLED_APPS = [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.sites",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        # Third party apps
        "admin_auto_filters",
        "django_object_actions",
        "django_fsm",
        "adminsortable2",
        "corsheaders",
        "dockerflow.django",
        "django_filters",
        "rest_framework",
        "parler",
        "marion",
        "howard",
        "easy_thumbnails",
        # Joanie
        "joanie.core",
        "joanie.payment",
        "joanie.badges",
        "joanie.demo",
    ]

    # Joanie
    JOANIE_LMS_BACKENDS = [
        {
            "API_TOKEN": values.Value(
                environ_name="EDX_API_TOKEN", environ_prefix=None
            ),
            "BACKEND": values.Value(environ_name="EDX_BACKEND", environ_prefix=None),
            "BASE_URL": values.Value(environ_name="EDX_BASE_URL", environ_prefix=None),
            "SELECTOR_REGEX": values.Value(
                r".*", environ_name="EDX_SELECTOR_REGEX", environ_prefix=None
            ),
            "COURSE_REGEX": values.Value(
                r".*", environ_name="EDX_COURSE_REGEX", environ_prefix=None
            ),
        }
    ]
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

    # Cache
    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    }

    JOANIE_ANONYMOUS_API_DEFAULT_CACHE_TTL = values.PositiveIntegerValue(
        3600, environ_prefix=None
    )  # 1 hour
    JOANIE_ANONYMOUS_SERIALIZER_DEFAULT_CACHE_TTL = values.PositiveIntegerValue(
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
        "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
        "PAGE_SIZE": 20,
        "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
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

    # Marion
    MARION_DOCUMENT_ISSUER_CHOICES_CLASS = "howard.defaults.DocumentIssuerChoices"
    MARION_CERTIFICATE_DOCUMENT_ISSUER = "howard.issuers.CertificateDocument"

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
            "joanie.payment.backends.payplug.PayplugBackend",
            environ_name="JOANIE_PAYMENT_BACKEND",
            environ_prefix=None,
        ),
        "configuration": {
            "secret_key": values.Value(
                "", environ_name="PAYPLUG_SECRET_KEY", environ_prefix=None
            ),
            "public_key": values.Value(
                "", environ_name="PAYPLUG_PUBLIC_KEY", environ_prefix=None
            ),
        },
    }

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

    # Easy thumbnails
    THUMBNAIL_EXTENSION = "webp"
    THUMBNAIL_TRANSPARENCY_EXTENSION = "webp"
    THUMBNAIL_ALIASES = {
        "core.Course.cover": {
            "1920w": {"size": (1920, 1080), "crop": "smart", "upscale": True},
            "1280w": {"size": (1280, 720), "crop": "smart", "upscale": True},
            "768w": {"size": (768, 432), "crop": "smart", "upscale": True},
            "384w": {"size": (384, 216), "crop": "smart", "upscale": True},
        },
        "core.Organization.logo": {
            "1024w": {"size": (1024, 1024), "crop": "smart", "upscale": True},
            "512w": {"size": (512, 512), "crop": "smart", "upscale": True},
            "256w": {"size": (256, 256), "crop": "smart", "upscale": True},
            "128w": {"size": (128, 128), "crop": "smart", "upscale": True},
        },
    }

    # Signature
    JOANIE_SIGNATURE_BACKEND = {
        "backend": values.Value(
            "joanie.signature.backends.lex_persona.client.LexPersonaClient",
            environ_name="JOANIE_SIGNATURE_BACKEND",
            environ_prefix=None,
        ),
        "configuration": {
            "base_url": values.Value(
                None, environ_name="JOANIE_LEX_PERSONA_BASE_URL", environ_prefix=None
            ),
            "consent_page_id": values.Value(
                None,
                environ_name="JOANIE_LEX_PERSONA_CONSENT_PAGE_ID",
                environ_prefix=None,
            ),
            "session_user_id": values.Value(
                None, environ_name="JOANIE_LEX_PERSONA_USER_ID", environ_prefix=None
            ),
            "profile_id": values.Value(
                None,
                environ_name="JOANIE_LEX_PERSONA_PROFILE_ID",
                environ_prefix=None,
            ),
            "token": values.Value(
                None, environ_name="JOANIE_LEX_PERSONA_TOKEN", environ_prefix=None
            ),
        },
    }

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
            )
            with sentry_sdk.configure_scope() as scope:
                scope.set_extra("application", "backend")


class Build(Base):
    """Settings used when the application is built.

    This environment should not be used to run the application. Just to build it with non-blocking
    settings.
    """

    SECRET_KEY = values.Value("DummyKey")
    STORAGES_STATICFILES_BACKEND = values.Value(
        "whitenoise.storage.CompressedManifestStaticFilesStorage"
    )


class Development(Base):
    """
    Development environment settings

    We set DEBUG to True and configure the server to respond from all hosts.
    """

    ALLOWED_HOSTS = ["*"]
    CORS_ALLOW_ALL_ORIGINS = True
    CSRF_TRUSTED_ORIGINS = ["http://localhost:3000", "http://localhost:8072"]
    DEBUG = True
    NGROK_ENDPOINT = values.Value(None, "NGROK_ENDPOINT", environ_prefix=None)

    SESSION_COOKIE_NAME = "joanie_sessionid"

    LOGIN_URL = "/admin/login/"
    LOGOUT_URL = "/admin/logout/"

    # Swagger security settings
    # e.g: For API routes which requires a jwt token to authenticate user, you can
    # fulfill this field with `Bearer <USER_JWT_TOKEN>`
    SWAGGER_SETTINGS = {
        "SECURITY_DEFINITIONS": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
            }
        }
    }

    def __init__(self):
        # pylint: disable=invalid-name
        self.INSTALLED_APPS += ["drf_yasg", "django_extensions"]


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
    }

    JOANIE_SIGNATURE_BACKEND = {
        "backend": "joanie.signature.backends.dummy.DummySignatureBackend",
    }

    JOANIE_ENROLLMENT_GRADE_CACHE_TTL = 0

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
                    "level": "DEBUG",
                },
            },
        }
    )

    def __init__(self):
        # pylint: disable=invalid-name
        self.INSTALLED_APPS += ["joanie.tests"]


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
    STORAGES_STATICFILES_BACKEND = values.Value(
        "whitenoise.storage.CompressedManifestStaticFilesStorage"
    )

    # Privacy
    SECURE_REFERRER_POLICY = "same-origin"

    # Media
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
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
