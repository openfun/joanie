output "objectstorage_bucket_name" {
  value = openstack_objectstorage_container_v1.joanie_media_storage.name
}

output "contracts_objectstorage_bucket_name" {
  value = openstack_objectstorage_container_v1.joanie_contracts_storage.name
}
