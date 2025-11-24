import google.generativeai as genai
import os
import json
from PIL import Image, ImageEnhance

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
        # DEBUG: Listar modelos disponíveis para diagnosticar erro 404
        print("--- Modelos Disponíveis nesta API Key ---")
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(f"Modelo: {m.name}")
        except Exception as e:
            print(f"Erro ao listar modelos: {e}")
        print("---------------------------------------")

        # Tenta usar o Flash (Gemini 2.0)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # 2. Carrega imagem
        img = Image.open(image_path)
        # --- 🔍 PRÉ-PROCESSAMENTO DE IMAGEM (TURBO) ---
        # 1. Aumenta o contraste drasticamente (separa tinta do papel)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)  # Fator 2.0 dobra o contraste

        # 2. Aumenta a nitidez (ajuda a definir as bordas das bolhas)
        enhancer_sharp = ImageEnhance.Sharpness(img)
        img = enhancer_sharp.enhance(1.5)
        
        # Salva um log visual (opcional, apenas para debug se quiser ver o resultado)
        # img.save("debug_enhanced.jpg")

        # --- 📉 OTIMIZAÇÃO DE TAMANHO ---
        # Redimensionar para largura máxima de 1080px (Full HD) mantendo a proporção.
        # Isso deixa o upload instantâneo e ajuda a IA a focar no padrão global.
        base_width = 1080
        if img.width > base_width:
            w_percent = (base_width / float(img.width))
            h_size = int((float(img.height) * float(w_percent)))
            # Usa LANCZOS para reduzir com alta qualidade
            img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)
            print(f"Imagem otimizada para: {img.size}")
        
        # 3. O Prompt Mágico (Ajustado para ignorar letras impressas)
        prompt = """
        Aja como um sistema de correção óptica rigoroso. Analise a imagem deste gabarito.
        Sua missão é identificar qual alternativa (A, B, C, D, E) foi REALMENTE PREENCHIDA pelo aluno.
        
        REGRAS VISUAIS CRÍTICAS:
        1. DIFERENCIE TINTA DE IMPRESSÃO:
           - Uma bolha VAZIA tem a letra (A, B, C...) impressa dentro com traço fino. ISSO NÃO É MARCAÇÃO.
           - Uma bolha MARCADA tem uma mancha de tinta escura (caneta) cobrindo a letra ou preenchendo o círculo.
        
        2. IGNORE SOMBRAS:
           - Se a imagem for foto de tela (monitor), ignore o padrão de pixels (moiré). Busque a marcação sólida.
        
        3. SAÍDA:
           - Identifique o número da questão.
           - Retorne a letra da bolha que tem TINTA DE CANETA.
           - Se houver dúvida, escolha a mais preenchida.
        
        RETORNE APENAS JSON:
        {
          "1": "A",
          "2": "C",
          "3": "E"
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