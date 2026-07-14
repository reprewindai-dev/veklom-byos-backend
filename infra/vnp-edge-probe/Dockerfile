FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VNP_KEY_DIR=/state

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY vnp_edge_probe.py .

VOLUME ["/state"]

EXPOSE 8000

CMD ["uvicorn", "vnp_edge_probe:app", "--host", "0.0.0.0", "--port", "8000"]
