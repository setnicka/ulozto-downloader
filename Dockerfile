FROM scratch AS builder

COPY requirements.txt ulozto-downloader.py ulozto-streamer.py /
COPY uldlib /uldlib/

FROM python:3.7

# Credits for original Dockerfile goes to: https://github.com/jansramek

RUN apt install apt-transport-https && \
    echo "deb https://deb.torproject.org/torproject.org stretch main" >> /etc/apt/sources.list && \
    echo "deb-src https://deb.torproject.org/torproject.org stretch main" >> /etc/apt/sources.list && \
    echo "deb http://ftp.de.debian.org/debian stretch main" >> /etc/apt/sources.list && \
    curl https://deb.torproject.org/torproject.org/A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89.asc | gpg --import && \
    gpg --export A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89 | apt-key add - && \
    apt update -y && \
    apt install -y libevent* && \
    apt install -y tor deb.torproject.org-keyring && \
    pip3 install --extra-index-url https://google-coral.github.io/py-repo/ tflite_runtime

EXPOSE 8000
WORKDIR /app

VOLUME ["/data","/download"]

ENV PYTHONUNBUFFERED=1 \
    TERM=xterm \
    DOWNLOAD_FOLDER=/download \
    DATA_FOLDER=/data \
    TEMP_FOLDER=/tmp \
    DEFAULT_PARTS=10 \
    AUTO_DELETE_DOWNLOADS=0

COPY --from=builder / ./

RUN pip3 install -r requirements.txt

CMD ["./ulozto-streamer.py"]
