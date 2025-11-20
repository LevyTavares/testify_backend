# Testify Backend

API em FastAPI para geração de gabaritos e correção de provas. Agora integrada ao Cloudinary para armazenamento permanente (URLs públicas) e preparada para rodar no Render (filesystem efêmero, uso de `/tmp`). Utiliza Google Gemini para correção automática.

## Requisitos

- Python 3.12+
- pip
- Conta no Cloudinary (para upload dos arquivos)
- Chave da API do Google Gemini (para correção via IA)

## Setup

```bash
# (opcional) criar e ativar um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS

# instalar dependências
pip install -r requirements.txt
```

### Variáveis de ambiente (Cloudinary e Gemini)

Defina as chaves do Cloudinary e do Gemini (localmente via export, e no Render via painel de env vars):

```bash
export CLOUDINARY_CLOUD_NAME=seu_cloud
export CLOUDINARY_API_KEY=seu_api_key
export CLOUDINARY_API_SECRET=seu_api_secret

# Gemini (Google Generative AI)
export GEMINI_API_KEY=seu_token_do_gemini
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
  - Observações (IA):
    - Usa o modelo `gemini-2.5-flash` (Google Generative AI) por padrão.
    - O prompt foi ajustado para diferenciar letras impressas dentro das bolhas (cinza claro, traço fino) de marcações reais a caneta.
    - É necessário definir `GEMINI_API_KEY` no ambiente.

## Observações

- Se for publicar, considere habilitar CORS conforme necessário.
- Não commite `.venv/` ou `__pycache__/` — já estão no `.gitignore`.
- Em produção (Render), garanta que as variáveis do Cloudinary estejam definidas. Sem elas, a geração falhará ao fazer upload.

### IA (Gemini) – detalhes rápidos

- Biblioteca: `google-generativeai` (veja `requirements.txt`).
- Modelo padrão: `gemini-2.5-flash` definido em `grade_it.py`.
- Debug de modelos disponíveis: após configurar o Gemini, o backend lista os modelos com suporte a `generateContent`. Isso ajuda a diagnosticar erros 404 de modelo não encontrado.
- Se necessário ajustar o modelo, altere a linha em `testify_backend/grade_it.py`:
  ```python
  model = genai.GenerativeModel('gemini-2.5-flash')
  ```

### Geração do gabarito – detalhes visuais

- Arquivo: `testify_backend/gen_gabarito.py`.
- As letras dentro das bolhas são desenhadas em cinza claro `(200,200,200)` com espessura `1` para não confundir a IA (traço fino, baixa saliência).
- O círculo da bolha permanece em preto `(0,0,0)` para manter a borda visível e o contraste.
