FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y libzbar0 && \
    pip install --upgrade pip

# Set working directory
WORKDIR /app

# Copy files into container
COPY . .

# Install Python dependencies
RUN pip install -r requirements.txt

# Start the bot
CMD ["python", "checkin_bot.py"]
