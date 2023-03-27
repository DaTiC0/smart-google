
# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.8.16-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME

# Install production dependencies.
COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# Copy local code to the container image.
COPY . ./

# Expose port 8080 to the world outside this container
ENV PORT 8080
EXPOSE $PORT

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
# Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to handle instance scaling.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app

# docker run --env-file=env_file_name