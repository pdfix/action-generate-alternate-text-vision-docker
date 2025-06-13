#!/bin/bash

# local docker test 

GREEN='\033[0;32m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print info messages
info() {
    echo -e "${PURPLE}$1${NC}"
}

# Function to print success messages
success() {
    echo -e "${GREEN}$1${NC}"
}

# Function to print error messages
error() {
    echo -e "${RED}ERROR: $1${NC}"
}

# init
pushd "$(dirname $0)" > /dev/null

EXIT_STATUS=0
img="alt-text-vision:test"
pltfm="--platform linux/amd64"
tmp_dir=".test"

info "Building docker image..."
docker build $pltfm --rm -t $img .

if [ -d "$(pwd)/$tmp_dir" ]; then
    rm -rf $(pwd)/$tmp_dir
fi
mkdir -p $(pwd)/$tmp_dir

info "List files in cwd"
docker run --rm $pltfm -v $(pwd):/data -w /data --entrypoint ls $img

info "Test #01: Show help"
docker run --rm $pltfm -v $(pwd):/data -w /data $img --help > /dev/null
if [ $? -eq 0 ]; then
    success "passed"
else
    error "Failed to run \"--help\" command"
    EXIT_STATUS=1
fi

info "Test #02: Extract config"
docker run --rm $pltfm -v $(pwd):/data -w /data $img config -o $tmp_dir/config.json > /dev/null
if [ -f "$(pwd)/$tmp_dir/config.json" ]; then
    success "passed"
else
    error "config.json not saved"
    EXIT_STATUS=1
fi

info "Test #03: Run update alternate text on tagged PDF"
docker run --rm $pltfm -v $(pwd):/data -w /data $img generate-alt-text -i example/PDFUA-1.pdf -o $tmp_dir/passed.pdf > /dev/null
if [ -f "$(pwd)/$tmp_dir/passed.pdf" ]; then
    success "passed"
else
    error "alt-text-vision to pdf failed on example/passed.pdf"
    EXIT_STATUS=1
fi

info "Test #04(fail test): Run update alternate text on PDF with no structure tree"
docker run --rm $pltfm -v $(pwd):/data -w /data $img generate-alt-text -i example/climate_change.pdf -o $tmp_dir/failed.pdf > /dev/null
if [ ! $? -eq 0 ]; then
    success "passed"
else
    error "alt-text-vision should fail on pdf that has no structure tree"
    EXIT_STATUS=1
fi

info "Removing testing docker image"
docker rmi $img

popd > /dev/null

if [ $EXIT_STATUS -eq 1 ]; then
    error "One or more tests failed."
    exit 1
else
    success "All tests passed."
    exit 0
fi
