# Base image from CircleCI. Contains python 3.8, node, jq, docker, docker-compose
FROM cimg/python:3.8-node

# Install python libraries needed for the scripts running here.
COPY requirements.txt /usr/share
RUN pip install --upgrade pip && \
  pip install -r /usr/share/requirements.txt

# Use root user to install binaries.
USER root
ENV GITHUB_HUB_VERSION 2.14.2

RUN wget -o /dev/null -O hub.tgz "https://github.com/github/hub/releases/download/v${GITHUB_HUB_VERSION}/hub-linux-amd64-${GITHUB_HUB_VERSION}.tgz"; \
  mkdir hub_dir; \
  tar -xvf hub.tgz --strip-components 1 -C hub_dir > /dev/null; \
  hub_dir/install; \
  rm -v hub.tgz; \
  rm -r hub_dir; \
  hub --version; \
  npm i -g json5

# Install gcloud package
RUN curl https://dl.google.com/dl/cloudsdk/release/google-cloud-sdk.tar.gz > /tmp/google-cloud-sdk.tar.gz && \
  mkdir -p /usr/local/gcloud && \
  tar -C /usr/local/gcloud -xvf /tmp/google-cloud-sdk.tar.gz && \
  /usr/local/gcloud/google-cloud-sdk/install.sh --quiet

# Adding gcloud to the path
ENV PATH $PATH:/usr/local/gcloud/google-cloud-sdk/bin

COPY docker-compose-up-remote-env stop-dockers-from-compose-up-remote-env get-github-repo /usr/bin/
COPY bin/* /usr/local/bin/
USER circleci
