# Optional containerized run — see README "Running locally" for the
# recommended local dev path.
FROM node:22-slim

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .

EXPOSE 3000
CMD ["npm", "run", "dev"]
