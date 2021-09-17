terraform {
  required_providers {
    openstack = {
      source = "terraform-provider-openstack/openstack"
      version = "1.46.0"
    }
  }

  backend "swift" {
    container = "joanie-terraform"
    archive_container = "joanie-terraform-archive"
  }

  required_version = ">= 1.0.0"
}
