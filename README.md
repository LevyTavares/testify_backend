# Testify Backend

API em FastAPI que recebe um payload com dados do gabarito e retorna uma imagem PNG gerada dinamicamente.

## Requisitos

- Python 3.12+
- pip

## Setup

```bash
# (opcional) criar e ativar um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS

# instalar dependências
pip install -r requirements.txt
```

## Rodar localmente

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

A API ficará disponível em `http://<SEU_IP_LOCAL>:8000`. Configure o app Expo para chamar esse endereço (use o IP da sua máquina na rede local, não `localhost`).

## Endpoints

- POST `/generate_template` — retorna `image/png` com o gabarito gerado.

## Observações

- Se for publicar, considere habilitar CORS conforme necessário.
- Não commite `.venv/` ou `__pycache__/` — já estão no `.gitignore`.
