#!/bin/bash

# Build script for PersonalMem Docker image

IMAGE_NAME="personalmem"
IMAGE_TAG="latest"

echo "Building PersonalMem Docker image..."
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Build successful!"
    echo ""
    echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
    echo ""
    echo "To run the container:"
    echo "  docker run -d -p 8888:8888 -p 27017:27017 \\"
    echo "    -e AZURE_OPENAI_API_KEY=your_key \\"
    echo "    -e AZURE_OPENAI_ENDPOINT=your_endpoint \\"
    echo "    -e AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini \\"
    echo "    -e AZURE_OPENAI_MODEL=gpt-4o-mini \\"
    echo "    --name personalmem ${IMAGE_NAME}:${IMAGE_TAG}"
    echo ""
    echo "Or use docker-compose:"
    echo "  docker compose up -d"
else
    echo "✗ Build failed!"
    exit 1
fi
