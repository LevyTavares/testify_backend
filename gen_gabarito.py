import cv2
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import math
import json
import os

 

def generate_gabarito_png_improved(
    filename="gabarito.png",
    num_questions=50,
    choices=("A", "B", "C", "D", "E"),
    margin=50,
    spacing_y=20,
    bubble_diameter=20,
    title="GABARITO FIXO",
    subtitle="Nome: _________________________   Numero: ____   Turma: ______",
    font_path=None,
    add_reference_marks=True
):
    try:
        # Try to find a common font
        if font_path is None:
            # Common font paths for different systems
            possible_fonts = [
                "arial.ttf",
                "Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/Library/Fonts/Arial.ttf",
                "C:/Windows/Fonts/arial.ttf"
            ]
            
            for font in possible_fonts:
                if os.path.exists(font):
                    font_path = font
                    break
            else:
                font_path = None
        
        if font_path:
            title_font = ImageFont.truetype(font_path, 60) 
            subtitle_font = ImageFont.truetype(font_path, 24)
            q_font = ImageFont.truetype(font_path, 28)
            choice_font = ImageFont.truetype(font_path, 28)
            header_font = ImageFont.truetype(font_path, 20)
        else:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            q_font = ImageFont.load_default()
            choice_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
    except Exception as e:
        print(f"Font warning: {e}, using default fonts")
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        q_font = ImageFont.load_default()
        choice_font = ImageFont.load_default()
        header_font = ImageFont.load_default()

    if num_questions > 10:
        columns = num_questions // 10
    else:
        columns = 1

    rows_per_col = math.ceil(num_questions / columns)
    estimated_row_height = spacing_y + bubble_diameter

    header_height = 40
    required_height = int(margin * 2 + header_height + 10 + rows_per_col * estimated_row_height + 50)

    calculated_width = 300 * columns
    page_size = (1240, 877)

    img = Image.new("RGB", page_size, "white")
    draw = ImageDraw.Draw(img)

    w, h = page_size

    # Get text dimensions for centering
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (w - title_width) // 2
    
    draw.text((title_x, margin//2), title, font=title_font, fill="black")
    top = margin + 15 + header_height
    bottom = h - margin
    usable_height = bottom - top
    col_width = (w - 2*margin) / columns
    row_height = min(spacing_y + bubble_diameter, usable_height / rows_per_col)

    bubble_positions = []

    q = 1
    for col in range(columns):
        x0 = margin + col * col_width
        x_question_num = x0 + 20
        temp_bbox = draw.textbbox((0,0), f"{q:02d}.", font=q_font)
        q_text_width = temp_bbox[2] - temp_bbox[0]
        x_choices_start = x_question_num + q_text_width + 30

        header_y = margin + 15
        for i, ch in enumerate(choices):
            cx = int(x_choices_start + i * (bubble_diameter + 20))
            bbox = draw.textbbox((0, 0), ch, font=header_font)
            w_ch = bbox[2] - bbox[0]
            h_ch = bbox[3] - bbox[1]
            tx = cx + (bubble_diameter - w_ch) / 2
            ty = header_y
            draw.text((tx, ty), ch, font=header_font, fill="black")

            line_y_start = ty + h_ch + 2
            line_y_end = top - 5
            if line_y_end > line_y_start:
                draw.line([(cx + bubble_diameter//2, line_y_start),
                          (cx + bubble_diameter//2, line_y_end)],
                         fill="black", width=1)

        for row in range(rows_per_col):
            if q > num_questions:
                break
            y = int(top + row * row_height)
            draw.text((x_question_num, y), f"{q:02d}.", font=q_font, fill="black")

            question_bubbles = []
            for i, ch in enumerate(choices):
                cx = int(x_choices_start + i * (bubble_diameter + 20))
                cy = int(y + (bubble_diameter/4) - bubble_diameter/2)

                # Draw bubble WITHOUT letter inside (clean for marking)
                draw.ellipse([cx, cy, cx + bubble_diameter, cy + bubble_diameter],
                           outline="black", width=2)

                # Store position for reference
                question_bubbles.append({
                    'choice': ch,
                    'center': (cx + bubble_diameter//2, cy + bubble_diameter//2),
                    'bbox': (cx, cy, cx + bubble_diameter, cy + bubble_diameter),
                    'header_pos': (cx + bubble_diameter//2, header_y)
                })

            bubble_positions.append({
                'question': q,
                'bubbles': question_bubbles,
                'question_pos': (x_question_num, y)
            })
            q += 1

    # Add reference marks for precise detection
    if add_reference_marks:
        mark_size = 15
        # Top-left: Cross pattern
        draw.line([(margin, margin), (margin+mark_size, margin)], fill="black", width=3)
        draw.line([(margin, margin), (margin, margin+mark_size)], fill="black", width=3)
        
        # Top-right: L pattern
        draw.line([(w-margin, margin), (w-margin-mark_size, margin)], fill="black", width=3)
        draw.line([(w-margin, margin), (w-margin, margin+mark_size)], fill="black", width=3)
        
        # Bottom-left: Square pattern
        draw.rectangle([(margin, h-margin-mark_size), (margin+mark_size, h-margin)],
                      outline="black", width=3)
        
        # Bottom-right: Circle pattern
        draw.ellipse([(w-margin-mark_size, h-margin-mark_size), (w-margin, h-margin)],
                    outline="black", width=3)

        # Add alignment marks along the sides
        for i in range(3):
            y_mark = margin + header_height + (h - 2*margin - header_height) * (i+1) // 4
            draw.line([(margin-15, y_mark), (margin-5, y_mark)], fill="black", width=2)
            draw.line([(w-margin+5, y_mark), (w-margin+15, y_mark)], fill="black", width=2)

    footer_text = "Assinale apenas uma opção por questão. Use caneta preta ou azul."
    bbox = draw.textbbox((0, 0), footer_text, font=subtitle_font)
    fw = bbox[2] - bbox[0]
    fh = bbox[3] - bbox[1]

    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (w - subtitle_width) // 2
    
    draw.text((subtitle_x, h - margin - 40), subtitle, font=subtitle_font, fill="black")
    draw.text((subtitle_x, h - margin - 15), footer_text, font=subtitle_font, fill="black")

    img.save(filename, dpi=(300,300))

    # Save bubble positions
    position_data = {
        'bubble_positions': bubble_positions,
        'page_size': page_size,
        'margin': margin,
        'bubble_diameter': bubble_diameter,
        'choices': choices
    }

    with open(filename.replace('.png', '_positions.json'), 'w') as f:
        json.dump(position_data, f, indent=2)

    return filename, position_data

def demonstrate_improved_layout():

    """Generate and display the improved layout"""
    template_path, position_data = generate_gabarito_png_improved(
        "./templates/gabarito_demo.png", 
        num_questions=15,
        add_reference_marks=True
    )
    
    print("Generated improved template with:")
    print("- Choice headers above bubbles")
    print("- Better spacing between question numbers and bubbles")
    print("- Reference marks for alignment")
    print(f"- Saved positions to: {template_path.replace('.png', '_positions.json')}")
    
    # Display the image
    img = Image.open(template_path)
    print(f"\nTemplate size: {img.size}")
    
    return template_path, position_data

# Gen
if __name__ == "__main__":
    # Print versions only when running this module directly
    print(f"OpenCV version: {cv2.__version__}")
    print(f"Pillow version: {Image.__version__}")
    print(f"NumPy version: {np.__version__}")

    template_path, position_data = demonstrate_improved_layout()

    