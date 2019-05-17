FROM ubuntu:19.04

RUN apt-get update
RUN apt-get install -y git python3 python3-venv python3-pip

RUN mkdir -p /install/garminexport
WORKDIR /install/garminexport/
ADD . .
RUN pip3 install -r requirements.txt
ENTRYPOINT ["python3", "backup-cycle.py"]