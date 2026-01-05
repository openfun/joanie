const removeImports = require("next-remove-imports")();

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  images: {
    // Disable image optimization, as the default image optimizer does not support static export
    unoptimized: true,
  },
  reactStrictMode: true,
  transpilePackages: [
    "@mui/x-date-pickers",
    "@mui/x-data-grid",
    "@mui/system",
  ],
  modularizeImports: {
    "@mui/icons-material": {
      transform: "@mui/icons-material/{{member}}", // To not import all package icons using top level import
    },
    "@mui/material": {
      transform: "@mui/material/{{member}}", // To not import all package icons using top level import
    },
  },
  turbopack: {},
};

module.exports = removeImports(nextConfig);
