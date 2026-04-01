FROM node:20-alpine AS builder
WORKDIR /app
COPY web/frontend/package*.json ./
RUN npm install
COPY web/frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY web/frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
