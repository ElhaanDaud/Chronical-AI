FROM python:3.11-slim

WORKDIR /app

# Install spaCy model at build time
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm && \
    python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
