import cv2
import numpy as np
import json
import os
import uuid
import cloudinary.uploader


def generate_and_upload_gabarito(num_questions, title, subtitle):
    # 1. Configuração A4 Vertical (Retrato) - Garantido
    width, height = 1240, 1754
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    position_data = {}
    corner_data = {}
    margin = 50

    # 2. Desenhar os 4 Cantos (Corner Anchors) - Essencial para correção
    cw, ch = 30, 30
    # TL, TR, BL, BR
    corners = [
        ("tl", margin, margin),
        ("tr", width - margin - cw, margin),
        ("bl", margin, height - margin - ch),
        ("br", width - margin - cw, height - margin - ch),
    ]
    for name, x, y in corners:
        cv2.rectangle(img, (x, y), (x + cw, y + ch), (0, 0, 0), -1)
        corner_data[name] = (x, y)

    position_data["corner_anchors"] = corner_data

    # 3. Cabeçalho
    cv2.putText(
        img,
        title,
        (int(width / 2) - 200, margin + 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (0, 0, 0),
        3,
    )
    cv2.putText(
        img,
        subtitle,
        (margin + 50, margin + 180),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 0),
        2,
    )

    # 4. Bolhas em 3 Colunas (Layout Vertical)
    num_cols = 3
    questions_per_col = int(np.ceil(num_questions / num_cols))
    col_width = width // num_cols

    q_num = 1
    for c in range(num_cols):
        start_x = (c * col_width) + margin + 20
        start_y = margin + 280
        for r in range(questions_per_col):
            if q_num > num_questions:
                break

            y = start_y + (r * 40)  # Espaçamento vertical
            cv2.putText(
                img,
                f"{q_num}.",
                (start_x, y + 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 0),
                2,
            )

            position_data[str(q_num)] = {}
            options = ["A", "B", "C", "D", "E"]
            for i, opt in enumerate(options):
                cx = start_x + 60 + (i * 55)
                cy = y
                # Bolha
                cv2.circle(img, (cx, cy), 14, (0, 0, 0), 2)
                # Letra
                cv2.putText(
                    img,
                    opt,
                    (cx - 8, cy + 6),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 0),
                    1,
                )
                # Salvar posição
                position_data[str(q_num)][opt] = (cx, cy)

            q_num += 1

    # 5. Salvar localmente com UUID (EVITA CACHE)
    unique_id = str(uuid.uuid4())
    temp_dir = "/tmp"
    os.makedirs(temp_dir, exist_ok=True)

    png_path = os.path.join(temp_dir, f"gabarito_{unique_id}.png")
    json_path = os.path.join(temp_dir, f"gabarito_{unique_id}.json")

    cv2.imwrite(png_path, img)
    with open(json_path, "w") as f:
        json.dump(position_data, f)

    # 6. Upload para Cloudinary e Limpeza
    try:
        png_res = cloudinary.uploader.upload(png_path, resource_type="image")
        json_res = cloudinary.uploader.upload(json_path, resource_type="raw")

        # Remove arquivos temporários
        if os.path.exists(png_path):
            os.remove(png_path)
        if os.path.exists(json_path):
            os.remove(json_path)

        return png_res["secure_url"], json_res["secure_url"]

    except Exception as e:
        print(f"Erro Cloudinary: {e}")
        raise e
        
