FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Dependencias pelas versoes travadas no lock: a imagem nao muda sozinha quando sai
# versao nova de alguma biblioteca. Vem antes do codigo para a camada ficar em cache.
COPY pyproject.toml requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

# --no-deps: as dependencias ja vieram do lock, aqui so entra o proprio pacote.
RUN pip install --no-cache-dir --no-deps .

RUN mkdir -p uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
