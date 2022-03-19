FROM python:3.10-slim-buster

WORKDIR /src

COPY . /src

RUN python -m pip install -U pip && python -m pip install -r requirements.txt
