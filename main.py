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
from gen_gabarito import generate_gabarito_png_improved
from grade_it import grade_gabarito_improved # Importa o corretor

# --- Novo fallback: gerar gabarito em branco (layout de bolhas) ---
def generate_gabarito_em_branco(tituloProva: str, numQuestoes: int):
    # Define o nome da pasta
    TEMPLATES_DIR = "templates"

    # Garante que a pasta 'templates' exista
    os.makedirs(TEMPLATES_DIR, exist_ok=True)

    # Gera um nome de arquivo único para evitar conflitos
    file_basename = str(uuid.uuid4())

    # Define os caminhos dentro da pasta 'templates'
    # (os.path.join lida com / ou \\ automaticamente)
    png_filename = os.path.join(TEMPLATES_DIR, f"{file_basename}.png")
    json_filename = os.path.join(TEMPLATES_DIR, f"{file_basename}_positions.json")

    try:
        # Chama a função importada do gen_gabarito.py
        # Ela salva o PNG e o JSON automaticamente
        generate_gabarito_png_improved(
            filename=png_filename,
            num_questions=numQuestoes,
            title=tituloProva,
            subtitle=f"Nome: ________ Matrícula: ________ Turma: ________"
        )

        # Retorna os caminhos dos DOIS arquivos gerados
        return png_filename, json_filename
    except Exception as e:
        print(f"Erro ao gerar gabarito: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao gerar imagem do gabarito")


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
            # Fluxo "em branco" (Sem Respostas)
            try:
                # 1. Chama a função (que salva os arquivos e retorna os caminhos)
                png_path, json_map_path = generate_gabarito_em_branco(
                    request_data.tituloProva,
                    request_data.numQuestoes
                )

                # 2. Retorna o ARQUIVO PNG, e coloca o map_path no Header
                return FileResponse(
                    png_path,
                    media_type="image/png",
                    headers={"X-Map-Path": json_map_path}
                )
            except HTTPException as e:
                raise e
            except Exception as e:
                print(e)
                raise HTTPException(status_code=500, detail="Falha ao processar gabarito em branco")
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
    file: UploadFile = File(...), # A imagem da câmera
    map_path: str = Form(...),    # O caminho do "mapa" JSON salvo no DB
    respostas: str = Form(...)    # As respostas corretas (como string JSON)
):
    # Define um caminho temporário para salvar a imagem recebida
    temp_image_path = os.path.join("templates", f"upload_{file.filename}")

    try:
        # Garante que a pasta 'templates' exista
        os.makedirs("templates", exist_ok=True)

        # Salva a imagem enviada no disco
        with open(temp_image_path, "wb") as buffer:
            buffer.write(await file.read())

        # Carrega o "mapa" de posições
        with open(map_path, 'r') as f:
            position_data = json.load(f)

        # Converte a string JSON de respostas em um array Python
        expected_answers = json.loads(respostas)

        # CHAMA O CORRETOR!
        grade_results = grade_gabarito_improved(
            image_path=temp_image_path,
            expected_answers=expected_answers,
            position_data=position_data,
            debug=False # Desliga o debug (não queremos pop-ups no servidor)
        )

        if grade_results is None:
            raise HTTPException(status_code=500, detail="Falha ao processar a correção")

        # Retorna o JSON completo com os resultados da correção
        return grade_results

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Arquivo de mapa JSON não encontrado no servidor.")
    except Exception as e:
        print(f"Erro na correção: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
    finally:
        # Limpa a imagem temporária
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)