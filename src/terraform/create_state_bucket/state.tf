# A separate terraform project that just creates the bucket where
# we will store the state. It needs to be created before the other
# project because that's where the other project will store its
# state. The state is encrypted using a KMS key because it will
# contain sensitive information.

terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "1.46.0"
    }
  }
  required_version = ">= 1.0.0"
}
