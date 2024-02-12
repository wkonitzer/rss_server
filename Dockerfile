# Use an official Python runtime as a parent image
FROM python:3.8-slim-bookworm

# Set the working directory to /app
WORKDIR /app

# Update, upgrade system packages, and clean up in a single layer
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files into the container at /app
COPY app.py get_latest_release.py config.py fetch_functions.py product_utils.py ./

# Make port 4000 available to the world outside this container
EXPOSE 4000

# Run as non-root user
RUN useradd -m myuser
USER myuser

# Run app.py when the container launches
CMD ["gunicorn", "--preload", "-w", "1", "-b", "0.0.0.0:4000", "app:app", "--access-logfile", "-", "--access-logformat", "%({X-Forwarded-For}i)s %(h)s - - [%(t)s] \"%(r)s\" %(s)s -"]