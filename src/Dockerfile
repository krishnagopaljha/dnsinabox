FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install gcc -y \
    && apt-get install libpq-dev -y \
    && apt-get clean

RUN apt-get install dnsutils -y
RUN apt-get install python3-dev default-libmysqlclient-dev build-essential pkg-config -y

# # Create a virtual environment
RUN python3 -m venv /venv

# Install psycopg2 inside the virtual environment
RUN /venv/bin/pip install psycopg2-binary

# Install requirements in the virtual environment
COPY ./requirements.txt /app/requirements.txt
RUN /venv/bin/pip install -r /app/requirements.txt

# Copy application code
COPY . /app/

# Set the virtual environment as the default for python and pip
ENV PATH="/venv/bin:$PATH"
