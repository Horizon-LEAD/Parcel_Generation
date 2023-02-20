FROM python:3.8.12-slim-bullseye

WORKDIR /srv/parcel-generation

RUN apt-get update && \
   apt-get install -y --no-install-recommends \
       liblapack-dev libatlas-base-dev && \
   rm -rf /var/lib/apt/lists/*

COPY setup.py requirements.txt README.md ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY src src
RUN pip install .

WORKDIR /

ENTRYPOINT [ "parcel-generation", "-vv" ]
