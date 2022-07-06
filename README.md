# Joanie – Power up Richie catalog 👛

Joanie aims to power up [Richie](https://github.com/openfun/richie) catalog
functionalities by delivering an API able to manage course
enrollment/subscription, payment and certificates delivery.

Joanie is built on top of [Django Rest
Framework](https://www.django-rest-framework.org/).

## Getting started

### Prerequisite

Make sure you have a recent version of Docker and [Docker
Compose](https://docs.docker.com/compose/install) installed on your laptop:

```bash
$ docker -v
  Docker version 20.10.2, build 2291f61

$ docker-compose -v
  docker-compose version 1.27.4, build 40524192
```

> ⚠️ You may need to run the following commands with `sudo` but this can be
> avoided by assigning your user to the `docker` group.

### Project bootstrap

The easiest way to start working on the project is to use GNU Make:

```bash
$ make bootstrap
```

This command builds the `app` container, installs dependencies, performs
database migrations and compile translations. It's a good idea to use this
command each time you are pulling code from the project repository to avoid
dependency-releated or migration-releated issues.

Now that your Docker services should be up and running 🎉

Note that if you need to run them afterwards, use the eponym Make rule:

```bash
$ make run
```

Now, you should be able to access to the API overview interface at
[http://localhost:8071/api/](http://localhost:8071/api/).

Finally, you can check all available Make rules using:

```bash
$ make help
```

If you're preparing for production, it is recommended to host media files in an
object storage.  We've cooked [Terraform](https://www.terraform.io/) scripts
and a [documentation](docs/media.md) to make it easy if, like us, you are
planning to use [Swift](https://docs.openstack.org/swift). Read more about it:
[docs/media.md](docs/media.md).

If you're planning to use AWS S3 or another object storage service, please let
us know by opening an [issue](https://github.com/openfun/joanie/issues) or even
better a [pull request](https://github.com/openfun/joanie/pulls) to add it to
the project.

### Django admin

You can access the Django admin site at
[http://localhost:8071/admin](http://localhost:8071/admin).

You first need to create a superuser account:

```bash
$ make superuser
```

## Guides

### Explanation

- [LMS Connection](https://github.com/openfun/joanie/blob/master/docs/explanation/lms-connection.md)
- [Payment backends](https://github.com/openfun/joanie/blob/master/docs/explanation/payment-backend.md)

## Contributing

This project is intended to be community-driven, so please, do not hesitate to
get in touch if you have any question related to our implementation or design
decisions.

We try to raise our code quality standards and expect contributors to follow
the recommandations from our
[handbook](https://openfun.gitbooks.io/handbook/content).

## License

This work is released under the MIT License (see [LICENSE](./LICENSE)).
