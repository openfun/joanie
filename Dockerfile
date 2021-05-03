# Joanie, power up Richie catalog

# ---- base image to inherit from ----
FROM python:3.8-slim as base

# Upgrade pip to its latest release to speed up dependencies installation
RUN python -m pip install --upgrade pip

# Upgrade system packages to install security updates
RUN apt-get update && \
  apt-get -y upgrade && \
  rm -rf /var/lib/apt/lists/*


# ---- Back-end builder image ----
FROM base as back-builder

WORKDIR /builder

# Copy required python dependencies
COPY src/backend /builder

RUN mkdir /install && \
  pip install --prefix=/install .

# ---- Core application image ----
FROM base as core

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install gettext
RUN apt-get update && \
  apt-get install -y \
  gettext && \
  rm -rf /var/lib/apt/lists/*

# Copy installed python dependencies
COPY --from=back-builder /install /usr/local

# Copy runtime-required files
COPY ./src/backend /app/
COPY ./docker/files/usr/local/bin/entrypoint /usr/local/bin/entrypoint

# Gunicorn
RUN mkdir -p /usr/local/etc/gunicorn
COPY docker/files/usr/local/etc/gunicorn/joanie.py /usr/local/etc/gunicorn/joanie.py

# Give the "root" group the same permissions as the "root" user on /etc/passwd
# to allow a user belonging to the root group to add new users; typically the
# docker user (see entrypoint).
RUN chmod g=u /etc/passwd

# Un-privileged user running the application
ARG DOCKER_USER
USER ${DOCKER_USER}

# We wrap commands run in this container by the following entrypoint that
# creates a user on-the-fly with the container user ID (see USER) and root group
# ID.
ENTRYPOINT [ "/usr/local/bin/entrypoint" ]

# ---- Development image ----
FROM core as development

# Switch back to the root user to install development dependencies
USER root:root

# Copy all sources, not only runtime-required files
COPY ./src/backend /app/

# Uninstall joanie and re-install it in editable mode along with development
# dependencies
RUN pip uninstall -y joanie
RUN pip install -e .[dev]

# Restore the un-privileged user running the application
ARG DOCKER_USER
USER ${DOCKER_USER}

# Target database host (e.g. database engine following docker-compose services
# name) & port
ENV DB_HOST=postgresql \
  DB_PORT=5432

# Run django development server
CMD python manage.py runserver 0.0.0.0:8000

# ---- Production image ----
FROM core as production

# The default command runs gunicorn WSGI server in joanie's main module
CMD gunicorn -c /usr/local/etc/gunicorn/joanie.py joanie.wsgi:application
