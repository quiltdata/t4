FROM ubuntu:16.04
MAINTAINER Quilt Data, Inc. contact@quiltdata.io

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y \
    nginx \
    curl \
    gettext \
    libssl-dev \
    build-essential \
    libpng-dev
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash -
RUN apt-get install -y nodejs

RUN mkdir /opt/app
WORKDIR /opt/app

# Install dependencies
COPY package.json .
COPY internals internals
RUN npm install

# Install the app
COPY app app
COPY static static
COPY server server
COPY config.json.example static/config.json
COPY federation.json.example static/federation.json
RUN npm run build
RUN npm run build:dll

# Set up nginx
COPY nginx-web.conf /etc/nginx/sites-available/default
RUN rm -rf /usr/share/nginx/html
RUN cp -r ./build/ /usr/share/nginx/html/
RUN cp static/config.json /usr/share/nginx/html/
RUN cp static/federation.json /usr/share/nginx/html/                        

# Run nginx
CMD exec nginx -g 'daemon off;'
