FROM python:3.12-alpine

# Install system dependencies
RUN apk add --no-cache gcc musl-dev linux-headers

# Set working directory
WORKDIR /app

# Copy all files
COPY . /app

# Install Python dependencies
# Using --no-cache-dir to reduce image size
RUN pip install --upgrade pip \
    && pip install --no-cache-dir .

# Expose the port the server runs on
EXPOSE 18000

# Run the MCP server using the installed script
CMD ["duckduckgo-mcp-server-sse"]
