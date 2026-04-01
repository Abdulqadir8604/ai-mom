FROM python:3.12-slim

# System deps for audio processing
RUN apt-get update && apt-get install -y ffmpeg git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy entire ai-mom project (pipeline lives at root)
COPY . .

# Install ai-mom deps
RUN pip install --no-cache-dir -r requirements.txt

# Install web api deps
RUN pip install --no-cache-dir -r web/api/requirements.txt

ENV PYTHONUNBUFFERED=1
ENV KMP_DUPLICATE_LIB_OK=TRUE

CMD ["uvicorn", "web.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
