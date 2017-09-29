# docker-circleci
Base image for the container we run on CircleCI 2.0 to build, tests and deploy Docker images for our web application.
The image contains Python 3 to allow to run a few scripts, and `docker` and `docker-compose` to build images (Docker inside Docker :).

To use it in your `.circleci/config.yml`, set the image hosted on Docker Hub to `bayesimpact/circleci`:
```
version: 2
jobs:
  build-and-test:
    docker:
      - image: bayesimpact/circleci
    steps:
      - checkout
      - setup_remote_docker
      - run: docker-composer build some-docker-service
      ...
```
