# ui/Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production
ARG UI_PORT=3000
ENV UI_PORT=${UI_PORT}
COPY --from=builder /app ./
EXPOSE ${UI_PORT}
CMD ["npm", "start"]
