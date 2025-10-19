# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Install curl for token retrieval
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the weather script
COPY get_weather.py .

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# Switch to non-root user
USER app

# Set environment for unbuffered output
ENV PYTHONUNBUFFERED=1

# Set the command to run the weather script directly
CMD ["python", "get_weather.py"]
