FROM node:22-slim

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy application files
COPY . .

# Build the application
RUN npm run build

# This vendored UACP/GPC runtime follows the canonical root runtime port contract.
# Production/root deployments must not fall back to forbidden ports 3000 or 8000.
ENV PORT=3010
EXPOSE 3010

# Start command
CMD ["npm", "run", "start"]
