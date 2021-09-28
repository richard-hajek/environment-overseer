FROM archlinux:latest

RUN pacman -Syu libfaketime python python-pip base-devel psmisc --noconfirm --needed

WORKDIR /app

ENV LD_PRELOAD=/usr/lib/faketime/libfaketime.so.1
ENV FAKETIME_TIMESTAMP_FILE="/time"

COPY . .

RUN pip install .


CMD ["bash", "/app/tests/routine.sh"]