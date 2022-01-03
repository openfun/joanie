# Media files in Joanie

Media files are kept private in Joanie and are not served on the web. They
are only used to render pdf documents with code using WeasyPrint via
[Marion](https://github.com/openfun/marion).

At [France Université Numérique](https://www.france-universite-numerique.fr),
we host our media files in [Swift](https://docs.openstack.org/swift) at
[OVHcloud](https://www.ovhcloud.com), and automate it with code using
[Terraform](https://www.terraform.io/).

> ✋ If you plan to develop locally on a site, you don't have to configure
> anything more. The following documentation targets operational users willing
> to setup a production infrastructure.

## OpenStack Users

To create the media files bucket via Terraform, you first need to create two
users in an OpenStack project:
- a user to run the Terraform script with admin role on object storage,
- a joanie user with no specific role. This is the user Django will use to
  access the media files bucket. Read and write accesses on the media files
  bucket will be granted specifically to this user by the Terraform script.

After creating the admin user, export its [`openrc.sh` file][1]. Create a new
directory under `env.d/terraform` with the name of your OpenStack project. For
example at FUN, we use 2 separate OpenStack projects: `fun_development` and
`fun_production`.

Place the `openrc.sh` file for the admin user under this directory.

> Note that you will be able to create several media files buckets per
> OpenStack project in case you want to host several environments in the same
> project. For example at FUN, the following environments are all in the
> `fun_development` project: `staging`, `preprod`, `PR branches`,...

Finally, edit the `openrc.sh` file and add the following variable with the
name of the second user you created for Django (by name we mean Keystone's
username).

```
export TF_VAR_user_name="joanie-user"
```

Your complete `env.d/terraform/production/openrc.sh` file should look
something like:

```
#!/bin/bash

# To use an Openstack cloud you need to authenticate against keystone, which
# returns a **Token** and **Service Catalog**. The catalog contains the
# endpoint for all services the user/tenant has access to - including nova,
# glance, keystone, swift.
#
export OS_AUTH_URL=https://auth.cloud.ovh.net/v3/
export OS_IDENTITY_API_VERSION=3

export OS_USER_DOMAIN_NAME=${OS_USER_DOMAIN_NAME:-"Default"}
export OS_PROJECT_DOMAIN_NAME=${OS_PROJECT_DOMAIN_NAME:-"Default"}


# With the addition of Keystone we have standardized on the term **tenant**
# as the entity that owns the resources.
export OS_TENANT_ID=f5h78jko9aex435gt3d4rfg76n1a3ze4
export OS_TENANT_NAME=2643565598702422

# In addition to the owning entity (tenant), openstack stores the entity
# performing the action as the **user**.
export OS_USERNAME="my-openstack-admin-user"

# With Keystone you pass the keystone password.
echo "Please enter your OpenStack Password: "
read -sr OS_PASSWORD_INPUT
export OS_PASSWORD=$OS_PASSWORD_INPUT

# If your configuration has multiple regions, we set that information here.
# OS_REGION_NAME is optional and only valid in certain environments.
export OS_REGION_NAME="GRA"
# Don't leave a blank variable, unset it if it was empty
if [ -z "$OS_REGION_NAME" ]; then unset OS_REGION_NAME; fi

# Configure the name of the Django user that will connect to the media bucket
export TF_VAR_user_name="joanie-user"
```

## Setup a shared Terraform state

> ✋ If the project already exists with a shared state, you should skip this
> section and start fetching the state locally to apply changes.

If the project doesn't exist at all, you will need to create a Swift bucket
to store your Terraform state file by typing the following commands in your
terminal:

```
$ bin/state init
$ bin/state apply
```

And voilà! Your shared state is now available to anyone contributing to the
project. It was placed in a bucket named `joanie-terraform` and a backup
bucket named `joanie-terraform-archive` was also created to historize all
changes.

## Create the media bucket

If everything went smoothly, it's time to initialize and run the main
terraform project using the shared state:

```
$ bin/terraform init
$ bin/terraform apply
```

A new bucket named `tf-default-joanie-media-storage` should
have been created in your OpenStack project.

To create a bucket for another environment in the same OpenStack project, we
make use of Terraform workspaces. By default, only the `default` workspace
exists (hence the "default" in the name of the bucket created above). For
example, you can create a new workspace for a `staging` environment _via_:

```
$ bin/terraform workspace new staging
```

And create the media files bucket for this environment as well:

```
$ bin/terraform apply
```

The new bucket will be named `tf-staging-joanie-media-storage`.

To list existing Terraform workspaces and switch to another one:

```
$ bin/terraform list
$ bin/terraform select {environment}
```

## Configure runtime environment

Once your media files bucket has been created for a targeted environment, you
will need to configure your project's runtime environment with the details and
secrets allowing your Django application to access it.

The following environment variables should be defined:

- `DJANGO_AWS_S3_ENDPOINT_URL`: the S3 compatible endpoint of your Swift
    service e.g. for OVH "https://s3.{region}.cloud.ovh.net"
- `DJANGO_AWS_ACCESS_KEY_ID` and `DJANGO_AWS_SECRET_ACCESS_KEY`: the S3
    credentials for your Joanie user in OpenStack, not the admin user!
- `DJANGO_AWS_S3_REGION_NAME`: the S3 region name of your hosting provider
    in which your media bucket was created

[1]: https://docs.openstack.org/newton/user-guide/common/cli-set-environment-variables-using-openstack-rc.html
