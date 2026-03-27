FROM node:20-alpine AS dashboard-builder
WORKDIR /frontend
COPY admin-frontend/package.json ./
RUN npm install
COPY admin-frontend/ ./
RUN npm run build

FROM python:3.11-alpine

RUN apk add --no-cache tzdata ca-certificates gcc musl-dev python3-dev
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo Asia/Shanghai > /etc/timezone

WORKDIR /app

COPY requirements.txt ./
RUN pip config set global.index-url http://mirrors.cloud.tencent.com/pypi/simple \
&& pip config set global.trusted-host mirrors.cloud.tencent.com \
&& pip install --upgrade pip \
&& pip install --no-cache-dir -r requirements.txt

COPY . /app
COPY --from=dashboard-builder /wxcloudrun/static/admin /app/wxcloudrun/static/admin

EXPOSE 80

CMD ["python", "manage.py", "runserver", "0.0.0.0:80"]
