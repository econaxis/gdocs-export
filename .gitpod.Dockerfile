FROM gitpod/workspace-full

USER gitpod

WORKDIR pydocs

COPY . .

RUN sudo apt-get update && \
    sudo apt-get install -y gcc libldap2-dev libsasl2-dev libssl-dev&& \
    pip3.8 install --upgrade pip && \
    pip3.8 install pyopenssl && \
    pip3.8 install -r installation/requirements.txt 

# Install custom tools, runtime, etc. using apt-get
# For example, the command below would install "bastet" - a command line tetris clone:
#
# RUN sudo apt-get -q update && \
#     sudo apt-get install -yq bastet && \
#     sudo rm -rf /var/lib/apt/lists/*
#
# More information: https://www.gitpod.io/docs/config-docker/
