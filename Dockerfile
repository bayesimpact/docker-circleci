FROM python:3

# Install docker and docker-compose to build the app containers.
RUN curl -sSL https://get.docker.com/ | sh

# Install library to deal with JSON in bash scripts.
RUN apt update -qqy && apt install jq -qqy

# Install sentry-cli to send release data on deployment.
RUN curl -sL https://sentry.io/get-cli/ | bash

# Install python libraries needed for the scripts running here.
RUN pip install --upgrade pip && \
  pip install awscli awscurl codecov docker-compose proselint python-keystoneclient python-swiftclient requests shyaml

# Install npm
RUN curl -sL https://deb.nodesource.com/setup_12.x | bash && apt install -qqy nodejs

ENV GITHUB_HUB_VERSION 2.3.0-pre8
RUN set -ex; \
  wget -O hub.tgz "https://github.com/github/hub/releases/download/v${GITHUB_HUB_VERSION}/hub-linux-amd64-${GITHUB_HUB_VERSION}.tgz"; \
  tar -xvf hub.tgz --strip-components 1 -C /usr/local; \
  rm -v hub.tgz; \
  hub --version

# Install gcloud package
RUN curl https://dl.google.com/dl/cloudsdk/release/google-cloud-sdk.tar.gz > /tmp/google-cloud-sdk.tar.gz && \
  mkdir -p /usr/local/gcloud && \
  tar -C /usr/local/gcloud -xvf /tmp/google-cloud-sdk.tar.gz && \
  /usr/local/gcloud/google-cloud-sdk/install.sh --quiet

# Adding gcloud to the path
ENV PATH $PATH:/usr/local/gcloud/google-cloud-sdk/bin

COPY docker-compose-up-remote-env stop-dockers-from-compose-up-remote-env get-github-repo /usr/bin/
