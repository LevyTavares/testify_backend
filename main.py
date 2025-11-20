# main.py - VERSÃO COMPLETA (Revisão 8 - Layout Minimalista Refinado)

# --- IMPORTAÇÕES ESSENCIAIS ---
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from pydantic import BaseModel, Field
from typing import List
import os  # Para variáveis de ambiente e caminhos
import uuid  # Para gerar nomes de arquivo únicos
import json  # Para converter as respostas
from gen_gabarito import generate_and_upload_gabarito, generate_gabarito_with_answers
from grade_it import grade_gabarito_improved  # Importa o corretor
import cloudinary
import cloudinary.uploader
import requests

# Configuração do Cloudinary (Render fornece via variáveis de ambiente)
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

# Pega o diretório de templates do Render, ou usa "templates" como padrão (usado apenas em fluxos legados)
TEMPLATES_DIR = os.environ.get("TEMPLATES_DIR", "templates")

# --- Configuração do Servidor FastAPI ---
app = FastAPI()

# Modelo para validar os dados recebidos do App (Pydantic)
class GabaritoRequest(BaseModel):
    tituloProva: str
    numQuestoes: int = Field(gt=0, description="Número total de questões")
    respostas: List[str] = None

# (Removido) Modelo de resposta JSON específico de streaming; agora retornamos URLs

@app.post("/generate_gabarito")
async def generate_gabarito_endpoint(request_data: GabaritoRequest):
    print(f"Recebido pedido: {request_data.tituloProva} ({request_data.numQuestoes} questões)")
    # VERIFICAÇÃO EXPLÍCITA SE EXISTEM RESPOSTAS
    if request_data.respostas and len(request_data.respostas) > 0:
        print(f"--- Gerando PREVIEW COLORIDO com {len(request_data.respostas)} respostas ---")
        try:
            # Transforma lista ["A", "B"] em dicionário {"1": "A", "2": "B"}
            answers_dict = {str(i+1): resp for i, resp in enumerate(request_data.respostas)}

            preview_url = generate_gabarito_with_answers(
                request_data.numQuestoes,
                request_data.tituloProva,
                "GABARITO OFICIAL",
                answers_dict
            )
            print(f"Preview gerado: {preview_url}")
            return {"preview_url": preview_url}
        except Exception as e:
            print(f"Erro ao gerar preview: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        print("--- Gerando GABARITO EM BRANCO para impressão ---")
        try:
            image_url, map_url = generate_and_upload_gabarito(
                request_data.numQuestoes,
                request_data.tituloProva,
                "Nome: ________________________________________"
            )
            return {"image_path": image_url, "map_path": map_url}
        except Exception as e:
            print(f"Erro ao gerar gabarito em branco: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# Endpoint raiz para teste
@app.get("/")
def read_root():
    return {"message": "Servidor do Gerador de Gabarito está online!"}

# --- Para rodar o servidor (use o comando uvicorn no terminal) ---
# Exemplo: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Endpoint final de correção usando o grade_it.py
@app.post("/corrigir_prova")
async def corrigir_prova(
    file: UploadFile = File(...),  # Imagem da câmera
    map_path: str = Form(...),     # URL do Cloudinary para o .json
    respostas: str = Form(...)     # String JSON das respostas
):
    TEMP_IMAGE_DIR = "/tmp"
    os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)
    temp_image_path = os.path.join(TEMP_IMAGE_DIR, f"upload_{uuid.uuid4()}.jpg")

    try:
        # 1. Salva a foto do aluno temporariamente
        with open(temp_image_path, "wb") as buffer:
            buffer.write(await file.read())

        # 2. Baixa o "mapa" JSON do Cloudinary
        response = requests.get(map_path)
        response.raise_for_status()  # Garante que o download funcionou
        position_data = response.json()  # Carrega o JSON

        # 3. Converte respostas
        expected_answers = json.loads(respostas)

        # 4. CHAMA O CORRETOR!
        grade_results = grade_gabarito_improved(
            image_path=temp_image_path,
            expected_answers=expected_answers,
            position_data=position_data,  # Passa o JSON baixado
            debug=False
        )
        # Lógica simplificada e segura:
        # Se tem "score" no resultado, é SUCESSO. Retorna o JSON.
        if grade_results and "score" in grade_results:
            return grade_results
            
        # Só lança erro se NÃO tiver score
        if "detail" in grade_results:
            print(f"Falha real: {grade_results['detail']}")
            raise HTTPException(status_code=422, detail=grade_results['detail'])

    except HTTPException as he:
        raise he  # Deixa o 422 passar limpo
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=404, detail="Arquivo de mapa JSON não encontrado no Cloudinary.")
    except Exception as e:
        print(f"Erro na correção: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
    finally:
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)