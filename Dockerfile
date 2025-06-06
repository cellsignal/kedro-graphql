FROM python:3.11.13-alpine3.20

COPY . /opt/kedro-graphql

## required to build psutil
RUN apk add gcc python3-dev musl-dev linux-headers

# Needed for pycurl (https://stackoverflow.com/a/50974082)
RUN apk add --no-cache libcurl
ENV PYCURL_SSL_LIBRARY=openssl

# Install packages only needed for building, install and clean on a single layer
RUN apk add --no-cache --virtual .build-dependencies build-base curl-dev \
    && pip install pycurl \
    && apk del .build-dependencies

WORKDIR /opt/kedro-graphql

RUN pip install -e .[ui]

EXPOSE 5000

CMD ["kedro", "gql", "--reload"]
