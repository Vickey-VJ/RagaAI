# Use an official Python runtime as a parent image
FROM python:3.11-slim-buster

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies that might be needed by some Python packages
# (e.g., for gTTS or other audio/data processing libraries)
# Add more if specific packages require them
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Expose a default port (FastAPI services typically run on 8000)
# This will be overridden by individual services in docker-compose.yml
EXPOSE 8000

# Default command to run - this will also likely be overridden
# For example, CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# We'll set specific commands in docker-compose.yml for each service.
CMD ["python"]
