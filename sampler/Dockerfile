FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg && \
    pip install kafka-python opencv-python-headless numpy
COPY app.py /app.py
ENTRYPOINT ["python", "/app.py"]

