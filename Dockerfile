# Use a Debian-based Python image for easier package management
FROM python:3.9-slim-buster

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
RUN apt-get update \
    && apt-get install -y nginx \
    && pip install espn_api flask gunicorn 
RUN rm -rf /root/.cache/pip \
    && rm -rf /var/lib/apt/lists/*

# Copy the Flask app to the container
WORKDIR /app
COPY . /app/

# Copy the Nginx configuration to the right place
COPY nginx.conf /etc/nginx/sites-available/default

# Expose ports for Nginx (80) and Gunicorn (8000)
EXPOSE 80 8000

# Start Nginx and the Flask app with Gunicorn
CMD service nginx start && gunicorn -w 4 main:app -b 0.0.0.0:8000
