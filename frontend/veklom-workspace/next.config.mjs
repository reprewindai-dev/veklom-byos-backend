/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "export",
  basePath: "/workspace-next",
  env: {
    NEXT_PUBLIC_API_BASE_URL: "",
  },
};
export default nextConfig;
