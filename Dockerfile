# Base image from CircleCI. Contains python 3.9, node, jq, docker, docker-compose
FROM cimg/python:3.9-node

# Install python libraries needed for the scripts running here.
COPY requirements.txt /usr/share
RUN pip install --upgrade pip && \
  pip install -r /usr/share/requirements.txt

# Use root user to install binaries.
USER root
ENV GITHUB_HUB_VERSION 2.14.2
ARG BAYES_DEV_SETUP_TAG=2021-05-12

RUN wget -o /dev/null -O hub.tgz "https://github.com/github/hub/releases/download/v${GITHUB_HUB_VERSION}/hub-linux-amd64-${GITHUB_HUB_VERSION}.tgz"; \
  mkdir hub_dir; \
  tar -xvf hub.tgz --strip-components 1 -C hub_dir > /dev/null; \
  hub_dir/install; \
  rm -v hub.tgz; \
  rm -r hub_dir; \
  hub --version; \
  npm i -g json5; \
  # Install commit message hook from bayes-developer-setup.
  wget -O /usr/local/bin/check-commit-msg "https://raw.githubusercontent.com/bayesimpact/bayes-developer-setup/${BAYES_DEV_SETUP_TAG}/hooks/commit-msg" && \
  chmod +x /usr/local/bin/check-commit-msg; \
  # Install Bazel; see https://docs.bazel.build/versions/main/install-ubuntu.html#install-on-ubuntu
  apt install apt-transport-https curl gnupg; \
  curl -fsSL https://bazel.build/bazel-release.pub.gpg | gpg --dearmor > bazel.gpg; \
  mv bazel.gpg /etc/apt/trusted.gpg.d/; \
  echo "deb [arch=amd64] https://storage.googleapis.com/bazel-apt stable jdk1.8" | sudo tee /etc/apt/sources.list.d/bazel.list; \
  apt update && apt install bazel

# Install gcloud package
RUN curl https://dl.google.com/dl/cloudsdk/release/google-cloud-sdk.tar.gz > /tmp/google-cloud-sdk.tar.gz && \
  mkdir -p /usr/local/gcloud && \
  tar -C /usr/local/gcloud -xvf /tmp/google-cloud-sdk.tar.gz && \
  /usr/local/gcloud/google-cloud-sdk/install.sh --quiet

# Adding gcloud and binaries to the path
ENV PATH $PATH:/usr/local/gcloud/google-cloud-sdk/bin:/usr/share/circleci/bin

COPY docker-compose-up-remote-env stop-dockers-from-compose-up-remote-env get-github-repo /usr/bin/
COPY bin/* /usr/share/circleci/bin/
RUN for file in $(ls /usr/share/circleci/bin/*.py); do mv $file ${file::-3}; done

USER circleci
