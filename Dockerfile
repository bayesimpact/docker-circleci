FROM python:3

#COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
#CMD ["/bin/sh"]

# Install docker and docker-compose to build the app containers.
RUN curl -sSL https://get.docker.com/ | sh

# Install python libraries needed for the scripts running here.
RUN pip install --upgrade pip && \
  pip install docker-compose requests shyaml
RUN dockerd -v; docker -v

#ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
