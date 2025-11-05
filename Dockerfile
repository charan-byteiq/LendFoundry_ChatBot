# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project directory into the container
COPY . .

# Make the start script executable
RUN chmod +x ./start.sh

# Expose the ports for the two backends and the Streamlit UI
EXPOSE 8000
EXPOSE 8001
EXPOSE 8501

# Command to run the application
CMD ["./start.sh"]
