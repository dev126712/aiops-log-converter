# Variables
IMAGE_NAME = ai-log-analyzer
LOG_NAME ?= your-app.log
DOCKERHUB_USERNAME = your_dockerhub_username
VERSION = 1.0.0

.PHONY: build run analyze

build:
	docker build -t $(IMAGE_NAME):$(VERSION) .

run:
	docker run --rm \
		--env-file .env \
		-v $(shell pwd)/$(LOG_NAME):/app/$(LOG_NAME) \
		$(IMAGE_NAME)

analyze: build run