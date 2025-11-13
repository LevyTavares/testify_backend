# main.py - VERSÃO COMPLETA (Revisão 8 - Layout Minimalista Refinado)

# --- IMPORTAÇÕES ESSENCIAIS ---
from fastapi import FastAPI, HTTPException #
from fastapi.responses import StreamingResponse #
from pydantic import BaseModel, Field #
from PIL import Image, ImageDraw, ImageFont # Pillow é importado como PIL
import math
import io
import os # Para checar a existência de fontes

# --- Novo fallback: gerar gabarito em branco (layout de bolhas) ---
def generate_gabarito_em_branco(tituloProva: str, numQuestoes: int):
    """Gera imagem de gabarito no novo layout de bolhas, totalmente em branco.

    Entradas:
    - tituloProva: título no topo do gabarito
    - numQuestoes: quantidade de questões a desenhar

    Saída: PIL.Image com o gabarito desenhado sem respostas preenchidas.
    """
    options = ['A', 'B', 'C', 'D', 'E']

    page_width = 1240
    page_height = 1754
    margin = 80
    line_spacing = 60
    circle_radius = 20
    circle_padding = 40  # Espaço entre círculos

    # Tenta encontrar um caminho de fonte válido (mesma heurística do endpoint)
    font_path = None
    possible_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for f in possible_fonts:
        if os.path.exists(f):
            font_path = f
            break

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

    # Título (centralizado)
    title_text = tituloProva.upper()
    title_width = draw.textlength(title_text, font=font_bold)
    x_title_pos = (page_width - title_width) / 2
    draw.text((x_title_pos, y_pos), title_text, fill="black", font=font_bold)
    title_bbox = draw.textbbox((x_title_pos, y_pos), title_text, font=font_bold)
    y_pos += (title_bbox[3] - title_bbox[1]) + 30

    # Adiciona campos do Aluno (Layout Flexível)
    try:
        # Tenta usar uma fonte um pouco maior para os campos
        field_font = ImageFont.truetype("LiberationSans-Regular.ttf", size=18)
    except Exception:
        field_font = ImageFont.load_default()

    line_y = y_pos + 20  # Posição Y das linhas
    field_text_y = y_pos + 5  # Posição Y dos rótulos

    # Largura útil da página (largura total - 2x a margem esquerda)
    usable_page_width = page_width - (2 * x_start)

    # --- Campo Nome ---
    x_nome = x_start
    label_nome = "Nome:"
    label_nome_width = draw.textlength(label_nome, font=field_font)
    line_nome_start = x_nome + label_nome_width + 10
    line_nome_end = x_nome + (usable_page_width * 0.55)  # 55% da largura

    draw.text((x_nome, field_text_y), label_nome, fill="black", font=field_font)
    draw.line([(line_nome_start, line_y), (line_nome_end, line_y)], fill="black", width=1)

    # --- Campo Matrícula ---
    x_matricula = line_nome_end + 20  # 20px de espaço
    label_matricula = "Matrícula:"  # ATUALIZADO
    label_matricula_width = draw.textlength(label_matricula, font=field_font)
    line_matricula_start = x_matricula + label_matricula_width + 10
    line_matricula_end = x_matricula + (usable_page_width * 0.25)  # 25% da largura

    draw.text((x_matricula, field_text_y), label_matricula, fill="black", font=field_font)
    draw.line([(line_matricula_start, line_y), (line_matricula_end, line_y)], fill="black", width=1)

    # --- Campo Turma ---
    x_turma = line_matricula_end + 20
    label_turma = "Turma:"
    label_turma_width = draw.textlength(label_turma, font=field_font)
    line_turma_start = x_turma + label_turma_width + 10
    line_turma_end = page_width - x_start  # Vai até a margem direita

    draw.text((x_turma, field_text_y), label_turma, fill="black", font=field_font)
    draw.line([(line_turma_start, line_y), (line_turma_end, line_y)], fill="black", width=1)

    y_pos += 60  # Espaço extra para os campos

    # Desenho das questões (sempre círculos vazios)
    start_options_x = x_start + 100  # Onde as bolhas começam (depois do número)
    for i in range(numQuestoes):
        # Número da questão
        question_num_text = f"{i+1:02}."
        draw.text((x_start, y_pos), question_num_text, fill="black", font=font_bold)

        # 5 opções vazias
        for j, option_text in enumerate(options):
            circle_x = start_options_x + (j * (circle_radius * 2 + circle_padding))
            box = [
                (circle_x - circle_radius, y_pos - circle_radius),
                (circle_x + circle_radius, y_pos + circle_radius)
            ]

            # Texto centralizado dentro do círculo
            bbox = font.getbbox(option_text)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            text_x = circle_x - (text_w / 2)
            text_y = y_pos - (text_h / 2) - 2

            # Sempre desenha o círculo vazio
            draw.ellipse(box, fill="white", outline="black", width=2)
            draw.text((text_x, text_y), option_text, fill="black", font=font)

        y_pos += line_spacing

        # Wrap para nova coluna simples quando necessário
        if y_pos + line_spacing > page_height - margin:
            x_start += (page_width // 2)
            start_options_x = x_start + 100
            y_pos = margin + 40

    # Instruções no rodapé
    y_instructions = page_height - 140  # Posição do rodapé de instruções
    draw.text((x_start, y_instructions), "Instruções:", fill="black", font=font_bold)
    y_instructions += 30
    draw.text((x_start, y_instructions), "• Pinte completamente o círculo da resposta.", fill="black", font=font)
    y_instructions += 25
    draw.text((x_start, y_instructions), "• Assinale apenas uma opção por questão.", fill="black", font=font)
    # Posição correta do rodapé: 30px abaixo da última instrução
    y_pos_footer = y_instructions + 30
    draw.text((x_start, y_pos_footer), "Gerado automaticamente - Testify", fill="#AAAAAA", font=font)
    return img


# --- Configuração do Servidor FastAPI ---
app = FastAPI()

# Modelo para validar os dados recebidos do App (Pydantic)
class GabaritoRequest(BaseModel):
    tituloProva: str
    numQuestoes: int = Field(gt=0, description="Número total de questões")
    respostas: list[str] | None = Field(default=None, description="Lista opcional com as respostas corretas (ex: ['B','A',...])")

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
        else:
            # Fallback novo: layout de bolhas totalmente em branco (sem preenchimento)
            img_pil = generate_gabarito_em_branco(
                tituloProva=request_data.tituloProva,
                numQuestoes=request_data.numQuestoes
            )

        # Prepara a imagem para envio
        img_io = io.BytesIO()
        img_pil.save(img_io, 'PNG', dpi=(150, 150)) # DPI ajustado
        img_io.seek(0)
        print("Imagem gerada com sucesso. Enviando resposta.")
        headers = {"Content-Disposition": 'inline; filename="gabarito.png"'}
        # Garante que o media_type está correto
        return StreamingResponse(img_io, media_type="image/png", headers=headers)
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