# Build the admin console as a static bundle and serve it through nginx.
# Build stage: install dependencies and compile the Vite project.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Expose build-time arguments so CI/CD can inject the API endpoint and OAuth config.
ARG VITE_API_BASE_URL
ARG VITE_OAUTH_CLIENT_ID
ARG VITE_DEFAULT_SCOPES="openid profile address email"
ARG VITE_OAUTH_CLIENT_SECRET
RUN set -e; \
    if [ -n "${VITE_API_BASE_URL:-}" ] || [ -n "${VITE_OAUTH_CLIENT_ID:-}" ] || \
    [ -n "${VITE_DEFAULT_SCOPES:-}" ] || [ -n "${VITE_OAUTH_CLIENT_SECRET:-}" ]; then \
    rm -f .env.production; \
    { \
    [ -n "${VITE_API_BASE_URL:-}" ] && printf "VITE_API_BASE_URL=%s\n" "${VITE_API_BASE_URL}" >> .env.production; \
    [ -n "${VITE_OAUTH_CLIENT_ID:-}" ] && printf "VITE_OAUTH_CLIENT_ID=%s\n" "${VITE_OAUTH_CLIENT_ID}" >> .env.production; \
    [ -n "${VITE_DEFAULT_SCOPES:-}" ] && printf "VITE_DEFAULT_SCOPES=%s\n" "${VITE_DEFAULT_SCOPES}" >> .env.production; \
    [ -n "${VITE_OAUTH_CLIENT_SECRET:-}" ] && printf "VITE_OAUTH_CLIENT_SECRET=%s\n" "${VITE_OAUTH_CLIENT_SECRET}" >> .env.production; \
    }; \
    fi; \
    npm run build

# Runtime stage: lightweight Nginx serving static files on port 3000.
FROM nginx:alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --spider --no-verbose http://127.0.0.1:3000 || exit 1
CMD ["nginx", "-g", "daemon off;"]
