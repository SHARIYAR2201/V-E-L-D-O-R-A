FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
ARG API_URL=http://api:8000
ENV API_URL=$API_URL
RUN npm run build
FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production API_URL=http://api:8000
COPY --from=build /app ./
EXPOSE 3000
CMD ["npm", "start"]
