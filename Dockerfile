FROM python:3.9-slim-bullseye

RUN apt update && apt install tor -y \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install tflite-runtime ulozto-downloader

ENTRYPOINT ["ulozto-downloader", "--output", "/downloads/"]
