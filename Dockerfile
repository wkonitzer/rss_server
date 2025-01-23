# Builder stage
FROM python:3.13-slim AS builder

# Install build dependencies and musl
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    musl \
    musl-dev \
    musl-tools \
    libc-dev \
    libxml2-dev \
    libxslt-dev \
    libstdc++6 \
    build-essential \
    libxml2 \
    libxslt1.1 \
    zlib1g \
    zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

# Install cython using pip
RUN pip install --no-cache-dir Cython --no-binary :all:  

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Upgrade pip and build wheels for dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip wheel --no-cache-dir --wheel-dir=/wheels $(grep -v lxml requirements.txt) && \
    rm -rf /wheels/lxml* && \
    LDFLAGS="-static" pip wheel --no-cache-dir --wheel-dir=/wheels lxml && \
    pip wheel --no-cache-dir --wheel-dir=/wheels --find-links=/wheels /wheels/*.whl

# Generate a list of all wheel files
RUN find /wheels -name "*.whl" > /wheels/wheels.txt    

# Copy application files
COPY . .

# Final stage: Distroless image
FROM cgr.dev/chainguard/python:latest

# Set working directory
WORKDIR /wheels

# Copy application files and wheels from the builder stage
COPY --from=builder /wheels /wheels/
COPY --from=builder /app/*.py /app/

# Switch to root
USER root

# Install dependencies using the python binary directly
RUN [ "python", "-m", "ensurepip" ]
RUN [ "python", "-m", "pip", "install", "--no-cache-dir", "--upgrade", "pip", "setuptools", "wheel" ]
RUN [ "python", "-m", "pip", "install", "--no-cache-dir", "--no-index", "--find-links=.", "-r", "wheels.txt" ]

# Remove wheels using Python
RUN ["python", "-c", "import shutil; shutil.rmtree('/wheels')"]

# Switch back to non-root user for security
USER nonroot

# Switch working directory back to /app
WORKDIR /app

# Expose port
EXPOSE 4000

# Command to run the app
CMD [ "-m", "gunicorn", "--preload", "-w", "1", "-b", "0.0.0.0:4000", "app:app", "--access-logfile", "-", "--access-logformat", "%({X-Forwarded-For}i)s %(h)s - - [%(t)s] \"%(r)s\" %(s)s -" ]
