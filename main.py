# main.py - VERSÃO COMPLETA (Revisão 8 - Layout Minimalista Refinado)

# --- IMPORTAÇÕES ESSENCIAIS ---
from fastapi import FastAPI, HTTPException #
from fastapi.responses import StreamingResponse #
from pydantic import BaseModel #
from PIL import Image, ImageDraw, ImageFont # Pillow é importado como PIL
import math
import io
import os # Para checar a existência de fontes

# --- Função generate_fixed_gabarito_png (REVISÃO 8 - Layout Minimalista Refinado) ---
def generate_fixed_gabarito_png(
    num_questions=50,
    choices=("A", "B", "C", "D", "E"),
    title="GABARITO",
    subtitle="Nome: ___ Numero: ___ Turma: ___", # Apenas referência
    font_path=None # Ex: "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
):
    # --- Configurações de Layout ---
    page_width = 1240
    page_height = 1754
    margin = 60 # Aumentei a margem geral
    line_color = (210, 210, 210) # Cinza um pouco mais claro
    text_color = (30, 30, 30)     # Cinza bem escuro (quase preto)
    label_color = (100, 100, 100) # Cinza médio para rótulos
    header_spacing = 20 # Espaço vertical no cabeçalho
    footer_height = 60
    num_columns = 5
    bubble_diameter = 28
    bubble_padding_h = 12
    bubble_spacing_h = bubble_diameter + bubble_padding_h
    question_num_padding = 18 # Aumentei um pouco
    row_padding_y = 22       # Aumentei um pouco

    # --- Carregar Fontes ---
    try:
        # Ajustei tamanhos para melhor hierarquia
        title_font_size = 36
        label_font_size = 18
        q_font_size = 20
        choice_font_size = 14
        footer_font_size = 14

        title_font = ImageFont.truetype(font_path, title_font_size) if font_path else ImageFont.load_default()
        label_font = ImageFont.truetype(font_path, label_font_size) if font_path else ImageFont.load_default()
        q_font = ImageFont.truetype(font_path, q_font_size) if font_path else ImageFont.load_default()
        choice_font = ImageFont.truetype(font_path, choice_font_size) if font_path else ImageFont.load_default()
        footer_font = ImageFont.truetype(font_path, footer_font_size) if font_path else ImageFont.load_default()
    except Exception:
        print("Aviso: Fonte TTF não encontrada. Usando fontes padrão.")
        # Usar fontes padrão se TTF falhar
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        q_font = ImageFont.load_default()
        choice_font = ImageFont.load_default()
        footer_font = ImageFont.load_default()

    # --- Criar Imagem ---
    img = Image.new("RGB", (page_width, page_height), "white")
    draw = ImageDraw.Draw(img)

    # --- Desenhar Cabeçalho ---
    current_y = margin
    # 1. Título (Alinhado à esquerda)
    draw.text((margin, current_y), title.upper(), font=title_font, fill=text_color)
    title_bbox = draw.textbbox((margin, current_y), title.upper(), font=title_font)
    current_y += (title_bbox[3] - title_bbox[1]) + header_spacing * 1.5 # Mais espaço após título

    # 2. Seção de Informações do Aluno (Layout Refinado)
    info_section_start_y = current_y
    line_length_nome = 400 # Linha maior para nome
    line_length_num_turma = 150 # Linhas menores
    field_spacing = 40 # Espaço entre campos (Nome | Número | Turma)

    # Função auxiliar para desenhar campo (Label + Linha)
    def draw_info_field(x, y, label_text, line_len):
        label_bbox = draw.textbbox((x, y), label_text, font=label_font)
        label_w = label_bbox[2] - label_bbox[0]
        label_h = label_bbox[3] - label_bbox[1]
        draw.text((x, y), label_text, font=label_font, fill=label_color)
        line_start_x = x + label_w + 8 # Linha começa pouco depois do label
        line_y_pos = y + label_h * 0.7 # Alinha a linha verticalmente com o texto
        draw.line([(line_start_x, line_y_pos), (line_start_x + line_len, line_y_pos)], fill=line_color, width=1)
        return x + label_w + 8 + line_len # Retorna a posição X final do campo desenhado

    # Desenha os campos sequencialmente
    last_x = draw_info_field(margin, info_section_start_y, "Nome:", line_length_nome)
    last_x = draw_info_field(last_x + field_spacing, info_section_start_y, "Número:", line_length_num_turma)
    draw_info_field(last_x + field_spacing, info_section_start_y, "Turma:", line_length_num_turma)

    # Linha divisória
    label_bbox_generic = draw.textbbox((0,0),"Nome:",font=label_font) # Pega altura de um label
    current_y = info_section_start_y + (label_bbox_generic[3]-label_bbox_generic[1]) + header_spacing
    draw.line([(margin, current_y), (page_width - margin, current_y)], fill=line_color, width=1)
    current_y += header_spacing * 1.5 # Mais espaço antes das questões

    # --- Calcular Área Útil e Colunas ---
    content_area_y_start = current_y
    content_area_y_end = page_height - margin - footer_height
    usable_width = page_width - 2 * margin
    usable_height = content_area_y_end - content_area_y_start
    estimated_row_draw_height = bubble_diameter + row_padding_y
    max_rows_per_col = max(1, int(usable_height // estimated_row_draw_height))
    if num_questions <= 0: num_questions = 1
    num_columns = math.ceil(num_questions / max_rows_per_col)
    col_width = usable_width / num_columns

    # --- Desenhar Questões ---
    q = 1
    for col in range(num_columns):
        col_start_x = margin + col * col_width

        max_q_num_text = f"{num_questions:02d}."
        max_q_num_bbox = draw.textbbox((0,0), max_q_num_text, font=q_font)
        max_q_num_width = max_q_num_bbox[2] - max_q_num_bbox[0]
        # Posição X final do número (para alinhar à direita antes das bolhas)
        q_num_x_end = col_start_x + max_q_num_width + 10 # Adiciona padding
        bubbles_start_x = q_num_x_end + question_num_padding # Início das bolhas

        for row in range(max_rows_per_col):
            if q > num_questions: break

            draw_center_y = content_area_y_start + row * estimated_row_draw_height + estimated_row_draw_height / 2

            # Desenhar número da questão
            q_num_text = f"{q:02d}."
            q_num_bbox = draw.textbbox((0,0), q_num_text, font=q_font)
            q_num_width = q_num_bbox[2] - q_num_bbox[0]
            q_num_height = q_num_bbox[3] - q_num_bbox[1]
            q_num_x = q_num_x_end - q_num_width # Alinha à direita
            q_num_y = draw_center_y - q_num_height / 2 # Centraliza vertical
            draw.text((q_num_x, q_num_y), q_num_text, font=q_font, fill=text_color)

            # Desenhar bolhas e letras
            for i, choice in enumerate(choices):
                bubble_center_x = bubbles_start_x + i * bubble_spacing_h + bubble_diameter / 2
                bubble_center_y = draw_center_y
                x0 = bubble_center_x - bubble_diameter / 2
                y0 = bubble_center_y - bubble_diameter / 2
                x1 = bubble_center_x + bubble_diameter / 2
                y1 = bubble_center_y + bubble_diameter / 2
                draw.ellipse([x0, y0, x1, y1], outline=line_color, width=1) # Bolha cinza claro

                choice_bbox = draw.textbbox((0,0), choice, font=choice_font)
                choice_w = choice_bbox[2] - choice_bbox[0]
                choice_h = choice_bbox[3] - choice_bbox[1]
                vertical_adjust = bubble_diameter * 0.05 # Ajuste vertical letra na bolha
                tx = bubble_center_x - choice_w / 2
                ty = bubble_center_y - choice_h / 2 - vertical_adjust
                draw.text((tx, ty), choice, font=choice_font, fill=text_color)

            q += 1

        if q > num_questions: break

    # --- Desenhar Rodapé (Instrução pequena e centralizada) ---
    instruction = "Assinale apenas uma opção por questão."
    instruction_bbox = draw.textbbox((0,0), instruction, font=footer_font)
    instruction_w = instruction_bbox[2] - instruction_bbox[0]
    instruction_h = instruction_bbox[3] - instruction_bbox[1]
    footer_y = page_height - margin - instruction_h # Posiciona acima da margem inferior
    draw.text(((page_width - instruction_w) / 2, footer_y), instruction, font=footer_font, fill=(180, 180, 180)) # Cinza bem claro

    # --- Retornar Imagem ---
    return img
# --- Fim da função generate_fixed_gabarito_png ---


# --- Configuração do Servidor FastAPI ---
app = FastAPI()

# Modelo para validar os dados recebidos do App (Pydantic)
class GabaritoRequest(BaseModel):
    tituloProva: str
    numQuestoes: int

# Endpoint que recebe os dados e retorna a imagem
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

        # Chama a função para gerar a imagem
        img_pil = generate_fixed_gabarito_png(
            num_questions=request_data.numQuestoes,
            title=request_data.tituloProva, # O título é usado no cabeçalho
            font_path=font_path
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