# Use an official Python runtime as a parent image
FROM python:3.8-slim-buster

# Set the working directory to /app
WORKDIR /app

# Copy only the requirements.txt first
COPY requirements.txt ./requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Copy the other specific files into the container at /app
COPY app.py ./app.py
COPY get_latest_release.py ./get_latest_release.py
COPY config.py ./config.py
COPY fetch_functions.py ./fetch_functions.py
COPY product_utils.py ./product_utils.py

# Make port 4000 available to the world outside this container
EXPOSE 4000

# Run app.py when the container launches
CMD ["gunicorn", "-b", "0.0.0.0:4000", "app:app"]
