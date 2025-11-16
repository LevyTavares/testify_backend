# Testify Backend

API em FastAPI para geração de gabaritos e correção de provas. Agora integrada ao Cloudinary para armazenamento permanente (URLs públicas) e preparada para rodar no Render (filesystem efêmero, uso de `/tmp`).

## Requisitos

- Python 3.12+
- pip
- Conta no Cloudinary (para upload dos arquivos)

## Setup

```bash
# (opcional) criar e ativar um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS

# instalar dependências
pip install -r requirements.txt
```

### Variáveis de ambiente (Cloudinary)

Defina as chaves do Cloudinary (localmente via export, e no Render via painel de env vars):

```bash
export CLOUDINARY_CLOUD_NAME=seu_cloud
export CLOUDINARY_API_KEY=seu_api_key
export CLOUDINARY_API_SECRET=seu_api_secret
```

No Render, o filesystem é efêmero. O backend salva arquivos temporariamente em `/tmp` e imediatamente faz upload para o Cloudinary; em seguida, remove os arquivos locais.

## Rodar localmente

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

A API ficará disponível em `http://<SEU_IP_LOCAL>:8000`. Configure o app Expo para chamar esse endereço (use o IP da sua máquina na rede local, não `localhost`).

## Endpoints

- GET `/` — healthcheck simples.
- POST `/generate_gabarito`
  - Body (JSON):
    ```json
    { "tituloProva": "Prova 1", "numQuestoes": 10 }
    ```
  - Resposta (JSON):
    ```json
    {
      "image_path": "https://res.cloudinary.com/.../gabarito.png",
      "map_path": "https://res.cloudinary.com/.../map.json"
    }
    ```
  - Observação: O backend gera PNG e um JSON de posições em `/tmp`, envia ambos para o Cloudinary e devolve as URLs permanentes (secure_url).
- POST `/corrigir_prova`
  - multipart/form-data:
    - `file`: imagem capturada (UploadFile)
    - `map_path`: URL (Cloudinary) para o arquivo `.json` de posições
    - `respostas`: string JSON com as respostas corretas, ex.: `"[\"A\",\"B\",...]"`
  - Resposta (JSON): resultado do `grade_gabarito_improved`.

## Observações

- Se for publicar, considere habilitar CORS conforme necessário.
- Não commite `.venv/` ou `__pycache__/` — já estão no `.gitignore`.
- Em produção (Render), garanta que as variáveis do Cloudinary estejam definidas. Sem elas, a geração falhará ao fazer upload.
