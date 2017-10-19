FROM python:3

# Install docker and docker-compose to build the app containers.
RUN curl -sSL https://get.docker.com/ | sh

# Install python libraries needed for the scripts running here.
RUN pip install --upgrade pip && \
  pip install docker-compose proselint requests shyaml

COPY docker-compose-up-remote-env stop-dockers-from-compose-up-remote-env /usr/bin/
