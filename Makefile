# Variables
IMAGE_NAME = ai-log-analyzer
LOG_NAME ?= raw_logs.txt

.PHONY: build run analyze

# 1. Build the image
build:
	docker build -t $(IMAGE_NAME) .

# 2. Run the container (Requires LOG_NAME to be passed)
run:
	docker run --rm \
		--env-file .env \
		-v $(shell pwd)/$(LOG_NAME):/app/$(LOG_NAME) \
		$(IMAGE_NAME)

# 3. All-in-one command
analyze: build run
