FROM node:24-slim

WORKDIR /app

# node_modules lives in its own volume (see docker-compose.yml), so the copy of package-lock.json the modules
# were installed from is kept beside them. Startup compares it with the current one and reinstalls when they
# differ, so pulling new dependencies needs only a restart, not a rebuild.
COPY package.json package-lock.json ./
RUN npm ci && cp package-lock.json node_modules/.installed-package-lock.json

COPY . .

EXPOSE 5173
CMD ["sh", "-c", "cmp -s package-lock.json node_modules/.installed-package-lock.json || { npm ci && cp package-lock.json node_modules/.installed-package-lock.json; } && exec npm run dev -- --host 0.0.0.0"]
