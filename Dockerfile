FROM python:3.15.2-slim

WORKDIR /app

COPY requirements.txt main.py ./
RUN pip install --no-cache-dir -r requirements.txt && opentelemetry-bootstrap -a install

ENV OTEL_SERVICE_NAME="github-token-broker"
ENV OTEL_TRACES_EXPORTER=otlp_proto_http
ENV OTEL_METRICS_EXPORTER=otlp_proto_http
ENV OTEL_LOGS_EXPORTER=otlp_proto_http
ENV OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
ENV OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true

EXPOSE 8080
ENV PORT=8080

CMD ["sh", "-c", "exec opentelemetry-instrument gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 8 main:app"]
