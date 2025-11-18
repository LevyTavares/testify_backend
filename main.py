# main.py - VERSÃO COMPLETA (Revisão 8 - Layout Minimalista Refinado)

# --- IMPORTAÇÕES ESSENCIAIS ---
from fastapi import FastAPI, HTTPException, Response, File, UploadFile, Form #
from fastapi.responses import StreamingResponse, FileResponse #
from pydantic import BaseModel, Field #
from PIL import Image, ImageDraw, ImageFont # Pillow é importado como PIL
import math
import io
import os # Para checar a existência de fontes
import uuid # Para gerar nomes de arquivo únicos
import json # Para converter as respostas
from gen_gabarito import generate_and_upload_gabarito
from grade_it import grade_gabarito_improved # Importa o corretor
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

# (Removido) Funções legadas de geração local e upload direto


# --- Configuração do Servidor FastAPI ---
app = FastAPI()

# Modelo para validar os dados recebidos do App (Pydantic)
class GabaritoRequest(BaseModel):
    tituloProva: str
    numQuestoes: int = Field(gt=0, description="Número total de questões")
    respostas: list[str] | None = Field(default=None, description="Lista opcional com as respostas corretas (ex: ['B','A',...])")

# (Removido) Modelo de resposta JSON não é mais usado, pois retornamos o arquivo PNG com header X-Map-Path

# Endpoint que recebe os dados e retorna a imagem
def generate_gabarito_com_respostas(respostas: list[str], title: str, font_path: str | None):
    """Gera imagem de gabarito vertical com instruções e círculos preenchidos para respostas corretas.

    Contrato:
    - entradas: respostas (lista de letras A-E), title (str), font_path (str|None)
    - saída: PIL.Image com gabarito desenhado
    - erro: se alguma letra não estiver em A-E, substitui por 'A' e continua (robustez)
    """
    options = ['A', 'B', 'C', 'D', 'E']
    # Sanitiza respostas (garante letras válidas)
    respostas_sanit = [r.upper() if r and r.upper() in options else 'A' for r in respostas]

    page_width = 1240
    page_height = 1754
    margin = 80
    line_spacing = 60
    circle_radius = 20
    circle_padding = 40  # Espaço entre círculos

    try:
        font_bold = ImageFont.truetype(font_path, 26) if font_path else ImageFont.load_default()
        font = ImageFont.truetype(font_path, 22) if font_path else ImageFont.load_default()
        font_small = ImageFont.truetype(font_path, 18) if font_path else ImageFont.load_default()
    except Exception:
        font_bold = ImageFont.load_default()
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()

    img = Image.new("RGB", (page_width, page_height), "white")
    draw = ImageDraw.Draw(img)

    x_start = margin
    y_pos = margin

    # Título
    draw.text((x_start, y_pos), title.upper(), fill="black", font=font_bold)
    title_bbox = draw.textbbox((x_start, y_pos), title.upper(), font=font_bold)
    y_pos += (title_bbox[3] - title_bbox[1]) + 30

    # Bloco de Instruções (pedido do usuário)
    draw.text((x_start, y_pos), "Instruções:", fill="black", font=font_bold)
    y_pos += 30
    draw.text((x_start, y_pos), "• Pinte completamente o círculo da resposta.", fill="black", font=font)
    y_pos += 25
    draw.text((x_start, y_pos), "• Assinale apenas uma opção por questão.", fill="black", font=font)
    y_pos += 50  # Mais espaço antes das questões

    # Desenho das questões
    start_options_x = x_start + 100  # Onde as bolhas começam (depois do número)
    for i, resposta_correta in enumerate(respostas_sanit):
        # Número da questão
        question_num_text = f"{i+1:02}."
        draw.text((x_start, y_pos), question_num_text, fill="black", font=font_bold)

        # Loop interno para 5 opções
        for j, option_text in enumerate(options):
            circle_x = start_options_x + (j * (circle_radius * 2 + circle_padding))
            box = [
                (circle_x - circle_radius, y_pos - circle_radius),
                (circle_x + circle_radius, y_pos + circle_radius)
            ]

            # Cálculo do posicionamento do texto centralizado
            bbox = font.getbbox(option_text)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            text_x = circle_x - (text_w / 2)
            text_y = y_pos - (text_h / 2) - 2  # Ajuste fino vertical

            if option_text == resposta_correta:
                # Círculo preenchido + letra branca
                draw.ellipse(box, fill="black", outline="black")
                draw.text((text_x, text_y), option_text, fill="white", font=font)
            else:
                # Círculo vazio
                draw.ellipse(box, fill="white", outline="black", width=2)
                draw.text((text_x, text_y), option_text, fill="black", font=font)

        y_pos += line_spacing

        # Se aproximando do final da página cria nova coluna simples (wrap vertical)
        if y_pos + line_spacing > page_height - margin:
            # Nova coluna
            x_start += (page_width // 2)
            start_options_x = x_start + 100
            y_pos = margin + 40  # Reinicia abaixo do título imaginário

    # Rodapé simples
    footer_text = "Gerado automaticamente - Testify"
    footer_bbox = draw.textbbox((0,0), footer_text, font=font_small)
    footer_w = footer_bbox[2] - footer_bbox[0]
    draw.text(((page_width - footer_w)/2, page_height - margin - 30), footer_text, fill="#555", font=font_small)
    return img

@app.post("/generate_gabarito")
async def generate_gabarito_endpoint(request_data: GabaritoRequest):
    try:
        print(f"Recebido pedido para gerar gabarito: {request_data.tituloProva} ({request_data.numQuestoes} questões)")
        # Tenta encontrar um caminho de fonte válido
        font_path = None
        possible_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            # Adicione outros caminhos comuns se necessário
        ]
        for font in possible_fonts:
            if os.path.exists(font):
                font_path = font
                print(f"Usando fonte: {font_path}")
                break
        if not font_path:
             print("Nenhuma fonte TTF encontrada nos caminhos padrão. Usando fonte default.")

        if request_data.respostas:
            # Usa nova função com respostas (ignora numQuestoes se tamanho divergir)
            img_pil = generate_gabarito_com_respostas(
                respostas=request_data.respostas,
                title=request_data.tituloProva,
                font_path=font_path
            )

            # Prepara a imagem para envio (mantém comportamento antigo para este caso)
            img_io = io.BytesIO()
            img_pil.save(img_io, 'PNG', dpi=(150, 150)) # DPI ajustado
            img_io.seek(0)
            print("Imagem gerada com sucesso. Enviando resposta.")
            headers = {"Content-Disposition": 'inline; filename="gabarito.png"'}
            return StreamingResponse(img_io, media_type="image/png", headers=headers)
        else:
            # Fluxo "em branco" (Sem Respostas) usando gerador autônomo com upload
            try:
                image_url, map_url = generate_and_upload_gabarito(
                    request_data.numQuestoes,
                    request_data.tituloProva,
                    "Nome: __________________ Data: ___/___/___",
                )
                return {"image_path": image_url, "map_path": map_url}
            except HTTPException as e:
                raise e
            except Exception as e:
                print(e)
                raise HTTPException(
                    status_code=500, detail="Falha ao processar gabarito em branco"
                )
    except Exception as e:
        print(f"Erro no servidor ao gerar imagem: {e}")
        # Retorna um erro HTTP 500 detalhado
        raise HTTPException(status_code=500, detail=f"Erro interno ao gerar imagem: {str(e)}")

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
        if "detail" in grade_results:
            # Se a correção falhou (ex: cantos não encontrados)
            if grade_results["score"] == 0:
                print(f"Falha na correção: {grade_results['detail']}")
                # Retorna o JSON de erro para o app
                raise HTTPException(status_code=422, detail=grade_results['detail'])

        # Se passou, retorna o JSON de sucesso
        return grade_results

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