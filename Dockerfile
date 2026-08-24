FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY breakfast_automation.py .
CMD ["python", "breakfast_automation.py"]
