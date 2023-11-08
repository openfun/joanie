
data "openstack_identity_auth_scope_v3" "current" {
  name = "current"
}

resource "openstack_objectstorage_container_v1" "joanie_media_storage" {
  name          = "tf-${terraform.workspace}-joanie-media-storage"
  provider      = openstack.ovh

  # all objects should be deleted from the container so that the container
  # can be destroyed without error.
  force_destroy = true

  metadata    = {
    workspace = terraform.workspace
  }

  # Bucket is in read only for anonymous users.
  # https://docs.openstack.org/swift/latest/overview_acl.html
  container_read = "${data.openstack_identity_auth_scope_v3.current.project_id}:${var.user_name}"
  container_write = "${data.openstack_identity_auth_scope_v3.current.project_id}:${var.user_name}"
}

resource "openstack_objectstorage_container_v1" "joanie_contracts_storage" {
  name          = "tf-${terraform.workspace}-joanie-contracts-storage"
  provider      = openstack.ovh

  # all objects should be deleted from the container so that the container
  # can be destroyed without error.
  force_destroy = true

  metadata    = {
    workspace = terraform.workspace
  }

  # Bucket is in read only for anonymous users.
  # https://docs.openstack.org/swift/latest/overview_acl.html
  container_read = "${data.openstack_identity_auth_scope_v3.current.project_id}:${var.user_name}"
  container_write = "${data.openstack_identity_auth_scope_v3.current.project_id}:${var.user_name}"
}
