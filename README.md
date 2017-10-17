# docker-circleci
Base image for the container we run on CircleCI 2.0 to build, tests and deploy Docker images for our web app.
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
      - run: |
          docker-compose build some-docker-service
          # Compose docker service with volumes (CircleCI 2.0 doesn not support this natively).
          ./docker-compose-up-remote-env.sh some-docker-service
          docker exec -t some-docker-service ./some-script-in-the-container.sh
          # Clean up docker service with volumes (they stayed up because of some sleep process).
          ./stop-dockers-from-compose-up-remote-env.sh
```
