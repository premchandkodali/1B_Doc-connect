# Use official Python image
FROM python:3.10-slim

# Set work directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --timeout=100 -r requirements.txt

# Copy the rest of the code
COPY . .
COPY run_doc_connect.sh /app/
RUN chmod +x /app/run_doc_connect.sh

# Expose port if your app runs a server (optional, e.g., 8000)
# EXPOSE 8000

## Entrypoint is now set in docker-compose.yml to use run_doc_connect.sh
