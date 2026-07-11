FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install .

COPY . .

EXPOSE 8089

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8089"]
