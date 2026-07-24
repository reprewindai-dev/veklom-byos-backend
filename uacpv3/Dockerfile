FROM node:22-slim

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy application files
COPY . .

# Build the application
RUN npm run build

# Expose the port the app runs on (assumed default for Vite/Express setup, typically 3000 or 5173, but we'll map whatever is needed. Render defaults to 10000 or 3000)
ENV PORT=3000
EXPOSE 3000

# Start command
CMD ["npm", "run", "start"]
