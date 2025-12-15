# Stage 1: Build the application
FROM node:20-alpine AS build

WORKDIR /app

# SvelteKit uses pnpm by default, but you can stick with npm
COPY package*.json ./
RUN npm install

COPY . .

# This runs `vite build`, which uses adapter-node to create a server
RUN npm run build

# Stage 2: Setup production environment
FROM node:20-alpine AS production

WORKDIR /app

# Copy production dependencies manifest
COPY package*.json ./
# Install only production dependencies
RUN npm install --omit=dev

# Copy the server from the build stage
COPY --from=build /app/build ./build
COPY --from=build /app/package.json ./package.json

# Expose the port the app runs on

EXPOSE 3000

# Environment variables will be read by the Node server
CMD ["node", "build/index.js"]