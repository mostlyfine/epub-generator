#!/bin/sh

docker images | grep epub-generator >/dev/null || docker build -t epub-generator .
docker run --rm -it -v $(pwd):/app/ epub-generator $1

