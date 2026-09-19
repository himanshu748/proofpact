FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY package*.json ./
RUN npm ci
COPY app ./app
COPY components ./components
COPY lib ./lib
COPY tsconfig.json next.config.ts ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM python:3.13-slim-bookworm
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter
COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/browsers
RUN playwright install --with-deps chromium
COPY --from=frontend /build/.next/standalone ./
COPY --from=frontend /build/.next/static ./.next/static
COPY backend ./backend
COPY infra/start.sh ./start.sh
RUN chmod +x ./start.sh
ENV PORT=8080 AWS_LWA_PORT=8080 AWS_LWA_READINESS_CHECK_PATH=/api/health AWS_LWA_ASYNC_INIT=true NEXT_TELEMETRY_DISABLED=1 COOKIE_SECURE=true DEMO_MODE=true
EXPOSE 8080
CMD ["/bin/bash","/app/start.sh"]
