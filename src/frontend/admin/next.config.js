/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  modularizeImports: {
    "@mui/icons-material": {
      transform: "@mui/icons-material/{{member}}", // To not import all package icons using top level import
    },
    "@mui/material": {
      transform: "@mui/material/{{member}}", // To not import all package icons using top level import
    },
  },
};

module.exports = nextConfig;
