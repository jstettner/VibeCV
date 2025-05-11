FROM python:3.11-slim
RUN pip install ultralytics kafka-python pillow
COPY worker.py /worker.py
ENTRYPOINT ["python", "/worker.py"]

