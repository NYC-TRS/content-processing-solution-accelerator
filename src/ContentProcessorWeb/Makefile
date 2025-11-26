# Makefile for ContentProcessorWeb deployment

# Variables
ACR_NAME := crstg6fsvw
RESOURCE_GROUP := msazaidocintstg
APP_NAME := ca-stg6fsvw-web
IMAGE_NAME := content-processor-web
TIMESTAMP := $(shell date +%s)
IMAGE_TAG := $(TIMESTAMP)
FULL_IMAGE := $(ACR_NAME).azurecr.io/$(IMAGE_NAME):$(IMAGE_TAG)
LATEST_IMAGE := $(ACR_NAME).azurecr.io/$(IMAGE_NAME):latest

.PHONY: deploy build push update-app login help clean

# Default target
deploy: login build push update-app
	@echo "✅ Deployment complete!"
	@echo "🌐 App URL: https://$(APP_NAME).blackplant-3f8c2e39.eastus.azurecontainerapps.io"

# Login to Azure Container Registry
login:
	@echo "🔐 Logging into Azure Container Registry..."
	@az acr login --name $(ACR_NAME)

# Build Docker image
build:
	@echo "🔨 Building Docker image with tag: $(IMAGE_TAG)"
	@docker build -t $(FULL_IMAGE) -t $(LATEST_IMAGE) .

# Push image to registry
push:
	@echo "📤 Pushing image to registry..."
	@docker push $(FULL_IMAGE)
	@docker push $(LATEST_IMAGE)

# Update container app with new image
update-app:
	@echo "🚀 Updating container app with new image..."
	@az containerapp update \
		--name $(APP_NAME) \
		--resource-group $(RESOURCE_GROUP) \
		--image $(FULL_IMAGE) \
		--query "properties.{Revision:latestRevisionName,Image:template.containers[0].image}" \
		-o table

# Build only (no deploy)
build-only:
	@echo "🔨 Building Docker image..."
	@docker build -t $(FULL_IMAGE) -t $(LATEST_IMAGE) .

# Clean up old Docker images
clean:
	@echo "🧹 Cleaning up old Docker images..."
	@docker images $(ACR_NAME).azurecr.io/$(IMAGE_NAME) --format "{{.ID}} {{.Tag}}" | grep -v latest | awk '{print $$1}' | xargs -r docker rmi -f

# Show help
help:
	@echo "Available targets:"
	@echo "  make deploy      - Full deployment (login + build + push + update)"
	@echo "  make build       - Build Docker image only"
	@echo "  make push        - Push image to registry"
	@echo "  make update-app  - Update container app"
	@echo "  make clean       - Remove old Docker images"
	@echo "  make help        - Show this help message"
