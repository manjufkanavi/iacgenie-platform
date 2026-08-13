FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY app.js .
EXPOSE 9091
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1:9091/health || exit 1
CMD ["node", "app.js"]
