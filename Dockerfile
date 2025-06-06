# Use the official Debian slim image with python 3.12 as a base (vision with old version in this project does not work with python 3.13)
FROM python:3.12-slim

# Update system and Install python3 and necessary dependencies
# RUN apt-get update && \
#     apt-get install -y \
#     python3-pip \
#     python3-venv \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

# Step by step to find out which is problematic
RUN apt-get update
RUN apt-get install -y python3-pip
RUN apt-get install -y python3-venv
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /usr/alt-desc/


# Create a virtual environment and install dependencies
ENV VIRTUAL_ENV=venv
RUN python3 -m venv venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY requirements.txt /usr/alt-desc/
RUN pip install --no-cache-dir -r requirements.txt && rm -rf /root/.cache/pip


# Copy config.json and the source code
COPY config.json /usr/alt-desc/
COPY src/ /usr/alt-desc/src/


# no longer run inside container as layer gets too big
# Copy script to download models into container and run it
# COPY download_models.py /usr/alt-desc/
# RUN venv/bin/python3 download_models.py

# Copy models data that we moved from original snapshot location
COPY model/ /usr/alt-desc/src/model


# Set Hugging Face environment variable to avoid online fetch
ENV TRANSFORMERS_OFFLINE=1


ENTRYPOINT ["/usr/alt-desc/venv/bin/python3", "/usr/alt-desc/src/main.py"]
