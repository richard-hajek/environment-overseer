FROM archlinux:latest

#RUN pacman -Syu --noconfirm && pacman -S libfaketime python python-pip base-devel --noconfirm --needed
RUN pacman -Syu libfaketime python python-pip base-devel --noconfirm --needed

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

ENV LD_PRELOAD=/usr/lib/faketime/libfaketime.so.1

RUN pacman -Syu psmisc --noconfirm --needed