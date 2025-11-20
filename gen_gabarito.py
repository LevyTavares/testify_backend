import cv2
import numpy as np
import json
import os
import uuid
import cloudinary.uploader
import unicodedata


def remove_accents(input_str):
    if input_str is None:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


def generate_and_upload_gabarito(num_questions, title, subtitle):
    # 1. Configuração A4 Vertical (Retrato) - 1240 x 1754
    width, height = 1240, 1754
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    position_data = {}
    corner_data = {}
    margin = 50

    # Tratamento de texto
    title = remove_accents(title)

    # 2. Desenhar os 4 Cantos (Corner Anchors) - Tamanho Aumentado (40px)
    cw, ch = 40, 40
    corners = [
        ("tl", margin, margin),
        ("tr", width - margin - cw, margin),
        ("bl", margin, height - margin - ch),
        ("br", width - margin - cw, height - margin - ch)
    ]
    for name, x, y in corners:
        cv2.rectangle(img, (x, y), (x + cw, y + ch), (0, 0, 0), -1)
        corner_data[name] = (x, y)

    position_data['corner_anchors'] = corner_data

    # 3. Cabeçalho (Layout Expandido)
    # Título
    cv2.putText(img, title, (int(width/2) - 250, margin + 100), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0,0,0), 4)

    # Linhas de Identificação
    line1 = "Nome: ________________________________________"
    cv2.putText(img, line1, (margin + 20, margin + 180), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,0), 2)

    line2 = "Matricula: ____________  Turma: ______  Data: __/__/__"
    cv2.putText(img, line2, (margin + 20, margin + 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,0), 2)

    # 4. Bolhas GIGANTES (Raio 22) em 3 Colunas
    num_cols = 3
    questions_per_col = int(np.ceil(num_questions / num_cols))
    col_width = width // num_cols

    # Ajustes de espaçamento para caber as bolhas grandes
    start_y_initial = margin + 350
    v_spacing = 65  # Espaço vertical entre linhas
    h_spacing = 50  # Espaço horizontal entre bolhas (compactado para compensar deslocamento)
    bubble_radius = 22

    q_num = 1
    for c in range(num_cols):
        # Centraliza a coluna
        start_x = (c * col_width) + margin + 10

        for r in range(questions_per_col):
            if q_num > num_questions:
                break

            y = start_y_initial + (r * v_spacing)

            # Número da questão
            cv2.putText(img, f"{q_num}.", (start_x, y+10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,0,0), 2)

            position_data[str(q_num)] = {}
            options = ["A", "B", "C", "D", "E"]

            for i, opt in enumerate(options):
                # Cálculo seguro de X para não estourar a margem
                cx = start_x + 70 + (i * h_spacing)
                cy = y

                # Bolha Grande
                cv2.circle(img, (cx, cy), bubble_radius, (0,0,0), 2)
                # Letra (Cinza bem claro para não confundir com marcação)
                cv2.putText(img, opt, (cx-10, cy+10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (210,210,210), 2)

                # Salvar posição central
                position_data[str(q_num)][opt] = (cx, cy)

            q_num += 1

    # 5. Salvar e Upload (UUID)
    unique_id = str(uuid.uuid4())
    temp_dir = "/tmp"
    os.makedirs(temp_dir, exist_ok=True)

    png_path = os.path.join(temp_dir, f"gabarito_{unique_id}.png")
    json_path = os.path.join(temp_dir, f"gabarito_{unique_id}.json")

    cv2.imwrite(png_path, img)
    with open(json_path, "w") as f:
        json.dump(position_data, f)

    try:
        png_res = cloudinary.uploader.upload(png_path, resource_type="image")
        json_res = cloudinary.uploader.upload(json_path, resource_type="raw")

        if os.path.exists(png_path):
            os.remove(png_path)
        if os.path.exists(json_path):
            os.remove(json_path)

        return png_res['secure_url'], json_res['secure_url']
    except Exception as e:
        print(f"Erro Cloudinary: {e}")
        raise e
        
