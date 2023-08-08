"""Parameters that define how the demo site will be built."""

DEFAULT_DEMO_DOMAIN = "localhost:8071"

NB_OBJECTS = {
    "organizations": 50,
    "products": 50,
    "courses": 100,
    "users": 10000,
    "enrollments": 30000,
    "max_orders_per_product": 50,
}

NB_DEV_OBJECTS = {
    "product_credential": 5,
    "product_certificate": 5,
    "course": 10,
}
