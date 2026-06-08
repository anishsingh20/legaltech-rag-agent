FROM python:3.12-slim

WORKDIR /app

COPY legaltech-rag-agent/requirements-serve.txt ./requirements-serve.txt
RUN pip install --no-cache-dir -r requirements-serve.txt

COPY rag_core.py serve.py ./

ENV RETRIEVAL_MODE=rest
EXPOSE 8080

CMD ["uvicorn", "serve:app", "--host", "0.0.0.0", "--port", "8080"]
