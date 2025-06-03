# Use the official Debian slim image with python 3.12 as a base (vision with old version in this project does not work with python 3.13)
FROM python:3.12-slim

# Update system and Install python3 and necessary dependencies
RUN apt-get update && \
    apt-get install -y \
    python3-pip \
    python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/alt-desc/


# Create a virtual environment and install dependencies
ENV VIRTUAL_ENV=venv
RUN python3 -m venv venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY requirements.txt /usr/alt-desc/
RUN pip install --no-cache-dir -r requirements.txt 


# Copy config.json and the source code
COPY config.json /usr/alt-desc/
COPY src/ /usr/alt-desc/src/


# Copy script to download models into container and run it
COPY download_models.py /usr/alt-desc/
RUN venv/bin/python3 download_models.py


ENTRYPOINT ["/usr/alt-desc/venv/bin/python3", "/usr/alt-desc/src/main.py"]
