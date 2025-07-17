#!/bin/bash

# This is local docker test during build and push action.

# Colors for output into console
GREEN='\033[0;32m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print info messages
info() { echo -e "${PURPLE}$1${NC}"; }

# Function to print success messages
success() { echo -e "${GREEN}$1${NC}"; }

# Function to print error messages
error() { echo -e "${RED}ERROR: $1${NC}"; }

# init
pushd "$(dirname $0)" > /dev/null

EXIT_STATUS=0
DOCKER_IMAGE="generate-alternate-text-vision:test"
PLATFORM="--platform linux/amd64"
TEMPORARY_DIRECTORY=".test"

info "Building docker image..."
docker build $PLATFORM -t $DOCKER_IMAGE .

if [ -d "$(pwd)/$TEMPORARY_DIRECTORY" ]; then
    rm -rf $(pwd)/$TEMPORARY_DIRECTORY
fi
mkdir -p $(pwd)/$TEMPORARY_DIRECTORY

info "List files in /usr/alt-desc"
docker run --rm $PLATFORM -v $(pwd):/data -w /data --entrypoint ls $DOCKER_IMAGE /usr/alt-desc/

info "Test #01: Show help"
docker run --rm $PLATFORM -v $(pwd):/data -w /data $DOCKER_IMAGE --help > /dev/null
if [ $? -eq 0 ]; then
    success "passed"
else
    error "Failed to run \"--help\" command"
    EXIT_STATUS=1
fi

info "Test #02: Extract config"
docker run --rm $PLATFORM -v $(pwd):/data -w /data $DOCKER_IMAGE config -o $TEMPORARY_DIRECTORY/config.json > /dev/null
if [ -f "$(pwd)/$TEMPORARY_DIRECTORY/config.json" ]; then
    success "passed"
else
    error "config.json not saved"
    EXIT_STATUS=1
fi

info "Test #03: Run generate alternate text on tagged PDF"
docker run --rm $PLATFORM -v $(pwd):/data -w /data $DOCKER_IMAGE generate-alt-text -i example/PDFUA-1.pdf -o $TEMPORARY_DIRECTORY/passed.pdf --model /model > /dev/null
if [ -f "$(pwd)/$TEMPORARY_DIRECTORY/passed.pdf" ]; then
    success "passed"
else
    error "generate alternate text on tagged pdf failed on example/PDFUA-1.pdf"
    EXIT_STATUS=1
fi

info "Test #04: Run generate alternate text on image"
docker run --rm $PLATFORM -v $(pwd):/data -w /data $DOCKER_IMAGE generate-alt-text -i example/image_example.jpg -o $TEMPORARY_DIRECTORY/image_example.txt --model /model > /dev/null
if [ -f "$(pwd)/$TEMPORARY_DIRECTORY/image_example.txt" ]; then
    success "passed"
else
    error "generate alternate text on image failed on example/image_example.jpg"
    EXIT_STATUS=1
fi

# Move this to functional testing part

# info "Test #04(fail test): Run update alternate text on PDF with no structure tree"
# docker run --rm $PLATFORM -v $(pwd):/data -w /data $DOCKER_IMAGE generate-alt-text -i example/climate_change.pdf -o $TEMPORARY_DIRECTORY/failed.pdf --model /model > /dev/null
# if [ ! $? -eq 0 ]; then
#     success "passed"
# else
#     error "alt-text-vision should fail on pdf that has no structure tree"
#     EXIT_STATUS=1
# fi

info "Cleaning up temporary files from tests"
rm -f $TEMPORARY_DIRECTORY/config.json
rm -f $TEMPORARY_DIRECTORY/passed.pdf
rm -f $TEMPORARY_DIRECTORY/image_example.txt
rmdir $(pwd)/$TEMPORARY_DIRECTORY

info "Removing testing docker image"
docker rmi $DOCKER_IMAGE

popd > /dev/null

if [ $EXIT_STATUS -eq 1 ]; then
    error "One or more tests failed."
    exit 1
else
    success "All tests passed."
    exit 0
fi
