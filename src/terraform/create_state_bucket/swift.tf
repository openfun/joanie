resource "openstack_objectstorage_container_v1" "backend" {
  name     = "joanie-terraform"
  provider = openstack.ovh

  # all objects should be deleted from the container so that the container
  # can be destroyed without error.
  force_destroy = true

  versioning {
    location = "joanie-terraform-archive"
    type     = "versions"
  }
}

resource "openstack_objectstorage_container_v1" "backend_archive" {
  name     = "joanie-terraform-archive"
  provider = openstack.ovh

  # all objects should be deleted from the container so that the container
  # can be destroyed without error.
  force_destroy = true
}
