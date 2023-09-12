// Override some environment variables for tests
process.env.NEXT_PUBLIC_API_ENDPOINT = "http://localhost:8071/api/v1.0/admin";
process.env.NEXT_PUBLIC_DJANGO_ADMIN_BASE_URL = "http://localhost:8071/admin";
process.env.NEXT_PUBLIC_API_SOURCE = "mocked"