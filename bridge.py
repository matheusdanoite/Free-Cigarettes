import os
import time
import requests
import json
import subprocess
import random
from PIL import Image, ImageOps, ImageDraw, ImageStat
try:
    import Vision
    import AppKit
    import Quartz
    from Foundation import NSURL
    HAS_VISION = True
except ImportError:
    HAS_VISION = False

from dotenv import load_dotenv

load_dotenv()

# Configuration
REMOTE_SERVER_URL = os.getenv("REMOTE_SERVER_URL", "http://localhost:5001")
WATCH_DIR = "print_queue"
POLL_INTERVAL = 5

def ensure_directories():
    if not os.path.exists(WATCH_DIR):
        os.makedirs(WATCH_DIR)
    if not os.path.exists("temp"):
        os.makedirs("temp")

ensure_directories()

def update_remote_status(filename, status):
    try:
        url = f"{REMOTE_SERVER_URL}/status/{filename}"
        requests.post(url, json={"status": status})
        print(f"Status [{filename}]: {status}")
    except Exception as e:
        print(f"Erro ao atualizar status remoto: {e}")

def detect_face_landmarks(image_path):
    if not HAS_VISION:
        return []
        
    try:
        url = NSURL.fileURLWithPath_(os.path.abspath(image_path))
        request_handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, None)
        
        # Criar o request usando new() ou alloc().init() de forma segura
        request = Vision.VNDetectFaceLandmarksRequest.new()
        
        # Tentar performRequests com diferentes assinaturas PyObjC
        try:
            res = request_handler.performRequests_error_([request], None)
            success = res[0] if isinstance(res, (tuple, list)) else res
        except Exception:
            res = request_handler.performRequests_error_([request])
            success = res[0] if isinstance(res, (tuple, list)) else res
            
        if not success:
            return []
            
        # Resultados podem ser método ou propriedade dependendo do ambiente
        results = request.results() if callable(request.results) else request.results
        if not results:
            return []
            
        faces = []
        for face in results:
            # extrair landmarks de forma segura
            landmarks_obj = face.landmarks() if callable(face.landmarks) else face.landmarks
            if not landmarks_obj: continue
            
            def extract_pts(region_attr):
                region = region_attr() if callable(region_attr) else region_attr
                if not region: return []
                count = region.pointCount() if callable(region.pointCount) else region.pointCount
                
                # Tentar normalizedPoints primeiro (mais robusto no PyObjC moderno)
                try:
                    norm_pts = region.normalizedPoints() if callable(region.normalizedPoints) else region.normalizedPoints
                    return [[pt.x, pt.y] for pt in [norm_pts[i] for i in range(count)]]
                except Exception:
                    # Fallback para pointAtIndex_ caso necessário (embora possa falhar em alguns ambientes)
                    try:
                        return [[pt.x, pt.y] for pt in [region.pointAtIndex_(i) for i in range(count)]]
                    except Exception:
                        return []

            # Bounding box também pode variar
            bbox = face.boundingBox() if callable(face.boundingBox) else face.boundingBox
                
            face_data = {
                "bbox": [bbox.origin.x, bbox.origin.y, bbox.size.width, bbox.size.height],
                "landmarks": {
                    "left_eye": extract_pts(landmarks_obj.leftEye),
                    "right_eye": extract_pts(landmarks_obj.rightEye),
                    "outer_lips": extract_pts(landmarks_obj.outerLips),
                    "nose": extract_pts(landmarks_obj.nose)
                }
            }
            faces.append(face_data)
        return faces
    except Exception as e:
        print(f"Erro na detecção Vision: {e}")
        import traceback
        traceback.print_exc()
        return []

def is_dark_area(img, pos, size):
    """
    Verifica se uma área da imagem é predominantemente escura.
    """
    try:
        # Converter para escala de cinza e pegar a região
        area = img.crop((pos[0], pos[1], pos[0] + size[0], pos[1] + size[1])).convert("L")
        # Calcular o brilho médio
        stat = area.load()
        w, h = area.size
        total = 0
        for y in range(h):
            for x in range(w):
                total += stat[x, y]
        avg = total / (w * h)
        return avg < 110 # Limiar para considerar "escuro"
    except Exception as e:
        print(f"Erro ao verificar brilho: {e}")
        return False

def is_frame_area_dark(img):
    """
    Verifica se o topo (30%) e as bordas (10px) da imagem são predominantemente escuros.
    Usado para decidir a cor da moldura (frame.png).
    """
    try:
        w, h = img.size
        # Converter para escala de cinza para facilitar cálculo de brilho
        img_l = img.convert("L")
        pixels = img_l.load()
        
        total_brightness = 0
        samples = 0
        
        # 1. Topo (30%)
        top_h = int(h * 0.3)
        for y in range(0, top_h, 2): # Passo de 2 para performance
            for x in range(0, w, 2):
                total_brightness += pixels[x, y]
                samples += 1
                
        # 2. Bordas laterais (10px) abaixo dos 30% do topo
        for y in range(top_h, h, 2):
            # Borda esquerda
            for x in range(min(10, w)):
                total_brightness += pixels[x, y]
                samples += 1
            # Borda direita
            for x in range(max(0, w - 10), w):
                total_brightness += pixels[x, y]
                samples += 1
                
        if samples == 0: return False
        avg = total_brightness / samples
        print(f"Brilho médio da área da moldura: {avg:.2f}")
        return avg < 120 # Limiar para inverter moldura para branco
    except Exception as e:
        print(f"Erro ao verificar brilho da moldura: {e}")
        return False

def apply_random_overlay(img, faces, force_white=None):
    """
    Nova lógica: se houver faces, bota cigarro em TODAS.
    Se não houver, bota uma moldura aleatória.
    force_white: se True, inverte moldura para branco.
    """
    items_dir = "png"
    w, h = img.size
    frames = ["frame_fro.png", "frame _s2.png"]
    
    if faces:
        print(f"Faces detectadas: {len(faces)}. Aplicando cigarro.")
        overlay_name = "cingarro.png"
        overlay_img = Image.open(os.path.join(items_dir, overlay_name)).convert("RGBA")
        
        for face in faces:
            fb_x, fb_y, fb_w, fb_h = face["bbox"]
            face_rect = [fb_x * w, (1 - fb_y - fb_h) * h, fb_w * w, fb_h * h]
            
            def get_avg_pt(pts):
                if not pts: return None
                avg_x = sum(p[0] for p in pts) / len(pts)
                avg_y = sum(p[1] for p in pts) / len(pts)
                return [face_rect[0] + avg_x * face_rect[2], 
                        face_rect[1] + (1 - avg_y) * face_rect[3]]
            
            mouth = get_avg_pt(face["landmarks"]["outer_lips"])
            if mouth:
                should_mirror = random.choice([True, False])
                scale = (face_rect[2] * 0.45) / overlay_img.width
                new_size = (int(overlay_img.width * scale), int(overlay_img.height * scale))
                
                new_ov = overlay_img.resize(new_size, Image.Resampling.LANCZOS)
                
                if should_mirror:
                    new_ov = ImageOps.mirror(new_ov)
                    pos = (int(mouth[0]), int(mouth[1]))
                else:
                    pos = (int(mouth[0] - new_size[0]), int(mouth[1]))
                
                # Cigarro usa preferência local ou global? Local é melhor para detalhes pequenos
                if is_dark_area(img, pos, new_size):
                    r, g, b, a = new_ov.split()
                    rgb_inverted = ImageOps.invert(Image.merge("RGB", (r, g, b)))
                    ir, ig, ib = rgb_inverted.split()
                    new_ov = Image.merge("RGBA", (ir, ig, ib, a))
                
                img.paste(new_ov, pos, new_ov)
    else:
        print("Nenhuma face. Aplicando moldura aleatória.")
        overlay_name = random.choice(frames)
        overlay_img = Image.open(os.path.join(items_dir, overlay_name)).convert("RGBA")
        
        scale_w = w / overlay_img.width
        scale_h = h / overlay_img.height
        scale = max(scale_w, scale_h)
        new_size = (int(overlay_img.width * scale), int(overlay_img.height * scale))
        pos = ((w - new_size[0]) // 2, (h - new_size[1]) // 2)
        
        new_ov = overlay_img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Usar preferência global (force_white) para molduras
        should_invert = force_white if force_white is not None else is_dark_area(img, pos, new_size)
        
        if should_invert:
            print(f"Moldura aleatória: Invertendo para Branco (preferência {'global' if force_white is not None else 'local'})")
            r, g, b, a = new_ov.split()
            rgb_inverted = ImageOps.invert(Image.merge("RGB", (r, g, b)))
            ir, ig, ib = rgb_inverted.split()
            new_ov = Image.merge("RGBA", (ir, ig, ib, a))
            
        img.paste(new_ov, pos, new_ov)
    
    return img

def apply_halftone(img, sample=3):
    """
    Aplica um efeito halftone de pontos na imagem para melhor visualização em impressão térmica.
    Otimizado para sample=3 (128 pontos em 384px) para ser mais pronunciado.
    """
    # 1. Converter para escala de cinza
    img = img.convert("L")
    w, h = img.size
    
    # Criar uma nova imagem branca para os pontos
    halftone = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(halftone)
    
    for x in range(0, w, sample):
        for y in range(0, h, sample):
            box = (x, y, min(x + sample, w), min(y + sample, h))
            region = img.crop(box)
            stat = ImageStat.Stat(region)
            if not stat.mean: continue
            avg = stat.mean[0]
            
            # Mais agressivo: se for bem claro, nem desenha. Se for escuro, desenha bem.
            ratio = 1 - (avg / 255.0)
            # Eleva ao quadrado para aumentar o contraste dos pontos
            radius = (sample / 1.5) * (ratio ** 1.2)
            
            if radius > 0.4:
                cx = x + (sample / 2.0)
                cy = y + (sample / 2.0)
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=0)
                
    return halftone

def process_with_apple_vision(input_path, output_path):
    """
    Pipeline Otimizado para Phomemo 384px:
    1. Check Bypass (Secret Menu)
    2. 9:16 Center Crop
    3. Resize 384px
    4. Detect Faces
    5. Cigarros ou Moldura Randômica
    6. Moldura evento obrigatória (frame.png) com contraste inteligente
    7. Conversão Grayscale
    8. Padding 10px
    """
    # 1. Bypass check - Prefix/Filename check
    filename = os.path.basename(input_path)
    if filename.startswith("raw_"):
        print(f"Bypass: {filename} detectado como menu secreto. Pulando pipeline.")
        # Apenas converte para grayscale e garante tamanho base se necessário, ou copia
        try:
            img = Image.open(input_path).convert("L")
            img.save(output_path)
            return True
        except Exception as be:
            print(f"Erro no bypass: {be}")
            return False

    print(f"Processando {input_path} (Thermal Pipeline 9:16)...")
    
    try:
        # 1. Carregar e Aplicar 9:16 Center Crop
        img_orig = Image.open(input_path).convert("RGBA")
        w_orig, h_orig = img_orig.size
        
        target_ratio = 9/16
        current_ratio = w_orig / h_orig
        
        if abs(current_ratio - target_ratio) > 0.02:
            print(f"Ajustando proporção para 9:16 (atual: {current_ratio:.2f})")
            if current_ratio > target_ratio:
                # Mais larga que 9:16 -> Cortar laterais
                new_w = int(h_orig * target_ratio)
                left = (w_orig - new_w) // 2
                img_orig = img_orig.crop((left, 0, left + new_w, h_orig))
            else:
                # Mais estreita que 9:16 -> Cortar topo/fundo
                new_h = int(w_orig / target_ratio)
                top = (h_orig - new_h) // 2
                img_orig = img_orig.crop((0, top, w_orig, top + new_h))
            w_orig, h_orig = img_orig.size

        # 2. Resize para 384px width
        new_w = 384
        new_h = int(h_orig * (new_w / w_orig))
        img = img_orig.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Salvar temporário para Vision detectar no tamanho correto
        temp_resize_path = input_path + ".res384.png"
        img.save(temp_resize_path)
        
        # 3. Detectar faces
        faces = detect_face_landmarks(temp_resize_path)
        if os.path.exists(temp_resize_path): os.remove(temp_resize_path)
        
        # DETERMINAR PREFERÊNCIA DE CONTRASTE (Global: Topo 30% + Bordas 10px)
        # Isso garante que a moldura principal e as secundárias fiquem visíveis.
        prefers_white = is_frame_area_dark(img)
        print(f"Preferência de contraste do pipeline: {'BRANCO' if prefers_white else 'PRETO'}")

        # 4. Aplicar Cigarros ou Moldura Random (passando preferência global para molduras)
        img = apply_random_overlay(img, faces, force_white=prefers_white)
        
        # 5. Aplicar Moldura Evento Obrigatória
        try:
            event_frame = Image.open("png/frame.png").convert("RGBA")
            ef_scale = max(img.width / event_frame.width, img.height / event_frame.height)
            ef_size = (int(event_frame.width * ef_scale), int(event_frame.height * ef_scale))
            ef_final = event_frame.resize(ef_size, Image.Resampling.LANCZOS)
            ef_pos = ((img.width - ef_size[0]) // 2, (img.height - ef_size[1]) // 2)
            
            if prefers_white:
                print("Invertendo frame.png obrigatório para branco.")
                r, g, b, a = ef_final.split()
                rgb_inverted = ImageOps.invert(Image.merge("RGB", (r, g, b)))
                ir, ig, ib = rgb_inverted.split()
                ef_final = Image.merge("RGBA", (ir, ig, ib, a))
                
            img.paste(ef_final, ef_pos, ef_final)
        except Exception as fe:
            print(f"Aviso: Não foi possível aplicar png/frame.png: {fe}")
        
        # 6. Converter para Escala de Cinza
        print("Convertendo para escala de cinza...")
        img_final = img.convert("L")
        
        # 7. Adicionar Padding de 15px na base (AUMENTA a altura total da imagem)
        final_w, final_h = img_final.size
        img_with_padding = Image.new("L", (final_w, final_h + 15), 255)
        img_with_padding.paste(img_final, (0, 0))
        
        temp_overlay_path = input_path + ".overlay.png"
        img_with_padding.save(temp_overlay_path)
        
        # 8. Processar final (DPI e compatibilidade)
        subprocess.run(["sips", "-s", "format", "png", temp_overlay_path, "--out", output_path], check=True, capture_output=True)
        
        if os.path.exists(temp_overlay_path):
            os.remove(temp_overlay_path)
            
        print("Processamento Otimizado (9:16 + Contraste) concluído.")
        return True
    except Exception as e:
        print(f"Erro no processamento pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False

def download_and_process():
    try:
        # 1. Checar por arquivos pendentes
        url = f"{REMOTE_SERVER_URL}/pending/" # Adicionado / para evitar redirects
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"Erro no servidor ({response.status_code}): {response.text[:100]}")
            return

        try:
            pending_files = response.json()
        except Exception as json_err:
            print(f"Erro ao ler JSON: {json_err}. Resposta bruta: '{response.text}'")
            return
        
        if not pending_files:
            return

        for filename in pending_files:
            update_remote_status(filename, "Me perdi aqui...")
            
            # 2. Download
            img_url = f"{REMOTE_SERVER_URL}/download/{filename}/"
            img_data = requests.get(img_url).content
            
            local_temp_path = os.path.join("temp", filename)
            if not os.path.exists("temp"): os.makedirs("temp")
            
            with open(local_temp_path, "wb") as f:
                f.write(img_data)
            
            # 3. Processamento Apple Vision (Apenas para imagens)
            final_output = os.path.join(WATCH_DIR, filename)
            ext = os.path.splitext(filename)[1].lower()
            
            if ext == '.txt':
                print(f"Arquivo de texto detectado. Movendo diretamente para {WATCH_DIR}")
                with open(final_output, "wb") as f:
                    f.write(img_data)
                success = True
            elif "raw_" in filename:
                print(f"Imagem RAW detectada ({filename}). Otimizando rotação e removendo molduras...")
                try:
                    img_orig = Image.open(local_temp_path).convert("RGBA")
                    # Achatar transparência para Branco (evita molduras pretas em PNGs transparentes)
                    img = Image.new("RGB", img_orig.size, (255, 255, 255))
                    img.paste(img_orig, mask=img_orig.split()[3])
                    
                    # Se for paisagem, rotacionar para retrato
                    if img.width > img.height:
                        print("Rotacionando imagem paisagem para retrato (RAW).")
                        img = img.rotate(90, expand=True)
                    
                    img.save(final_output)
                    success = True
                except Exception as e:
                    print(f"Erro ao tratar imagem RAW: {e}")
                    success = False
            else:
                success = process_with_apple_vision(local_temp_path, final_output)
            
            if success:
                update_remote_status(filename, "Olhe a impressora")
                
                # Deletar o arquivo temporário original após processamento bem sucedido
                if os.path.exists(local_temp_path):
                    os.remove(local_temp_path)
                    print(f"Limpeza: Arquivo temporário {local_temp_path} removido.")
                
                # O script print_phomemo.py já deve estar monitorando a pasta WATCH_DIR
                # Ele vai detectar o arquivo, imprimir e mover para 'processed'
                
                # 4. Avisar servidor que foi processado
                requests.delete(f"{REMOTE_SERVER_URL}/processed/{filename}/")
                
                # O status "Pronto" agora é enviado diretamente pelo print_phomemo.py ao finalizar a impressão.
            else:
                update_remote_status(filename, "Erro no processamento")

    except Exception as e:
        print(f"Erro no ciclo de bridge: {e}")

def main():
    print(f"Bridge Local Iniciada - Monitorando {REMOTE_SERVER_URL}")
    print(f"Salvando resultados em: {os.path.abspath(WATCH_DIR)}")
    
    while True:
        download_and_process()
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
