

build:
	@podman build -v /home/henry/.cache/pip:/root/.cache/pip -t gdocs-export .
push:
	@podman push gdocs-export henry2833/gdocs-export:latest

all: build push


