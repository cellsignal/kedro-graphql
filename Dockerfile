FROM python:3.11.9-alpine3.19

COPY . /opt/kedro-graphql

## required to build psutil
RUN apk add --no-cache gcc python3-dev musl-dev linux-headers libcurl

WORKDIR /opt/kedro-graphql

RUN apk add --virtual .build-deps curl-dev \
    && pip install -e . \
    && apk --purge del .build-deps

CMD ["kedro", "gql", "--reload"]
