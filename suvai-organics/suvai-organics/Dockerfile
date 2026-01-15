# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements-docker.txt requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set environment variable for Flask
ENV FLASK_APP=app.py

# Expose port 5000 for the Flask app
EXPOSE 5000

# Run app.py when the container launches
CMD ["python", "app.py"]
