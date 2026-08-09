# --- build stage ---
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Live mode; nginx proxies /api to the api service (same origin, no CORS needed).
ENV VITE_USE_MOCKS=false
ENV VITE_API_BASE=/api
RUN npm run build

# --- serve stage ---
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
