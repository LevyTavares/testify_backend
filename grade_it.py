import google.generativeai as genai
import os
import json
from PIL import Image

# Função dummy para compatibilidade (caso o main tente chamar)
def detect_corner_anchors(image):
    return None

def grade_gabarito_improved(image_path, expected_answers, position_data=None, debug=False):
    """
    Corrige a prova usando Google Gemini 1.5 Flash.
    """
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERRO CRÍTICO: GEMINI_API_KEY não encontrada.")
        return {"score": 0, "acertos": 0, "erros": 0, "total": 0, "detail": "Erro no servidor: Falta API Key."}

    try:
        print("--- 🤖 Iniciando análise com Gemini AI ---")
        
        # 1. Configura a IA
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # 2. Carrega imagem
        img = Image.open(image_path)
        
        # 3. Prompt
        prompt = """
        Aja como um corretor de gabaritos. Analise a imagem.
        Identifique a alternativa preenchida (A, B, C, D, E) para cada questão numérica.
        Ignore sombras. Se houver rasura, considere ANULADA.
        
        RETORNE APENAS JSON:
        {
          "1": "A",
          "2": "C"
        }
        """
        
        # 4. Envia
        response = model.generate_content([prompt, img])
        
        # 5. Limpa resposta
        text = response.text.strip().replace("```json", "").replace("```", "")
        detected_answers = json.loads(text)
        print(f"✅ IA Detectou: {detected_answers}")

        # 6. Calcula Nota
        acertos = 0
        erros = 0
        total = len(expected_answers)
        
        for i, correta in enumerate(expected_answers):
            num = str(i + 1)
            correta = str(correta).upper().strip()
            aluno = str(detected_answers.get(num, "NULA")).upper().strip()
            
            if aluno == correta:
                acertos += 1
            else:
                erros += 1
        
        score = (acertos / total) * 10
        
        return {
            "score": round(score, 1),
            "acertos": acertos,
            "erros": erros,
            "total": total,
            "detail": "Correção via IA concluída."
        }

    except Exception as e:
        print(f"❌ Erro IA: {e}")
        return {"score": 0, "detail": "Falha na IA. Tente novamente."}