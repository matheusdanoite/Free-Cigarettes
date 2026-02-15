import asyncio
import sys
import time
import os
import shutil
import requests
from bleak import BleakScanner, BleakClient
from PIL import Image, ImageDraw, ImageFont, ImageOps

# For PDF support (optional if pymupdf is installed)
try:
    import fitz
except ImportError:
    fitz = None

from dotenv import load_dotenv

load_dotenv()

# UUIDs discovered
WRITE_CHARACTERISTIC_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"
NOTIFY_CHARACTERISTIC_UUID = "0000ff03-0000-1000-8000-00805f9b34fb"

# Printer Width (Dots)
PRINTER_WIDTH = 384

# Directions
WATCH_DIR = "print_queue"
PROCESSED_DIR = os.path.join(WATCH_DIR, "processed")

def ensure_directories():
    if not os.path.exists(WATCH_DIR):
        os.makedirs(WATCH_DIR)
    if not os.path.exists(PROCESSED_DIR):
        os.makedirs(PROCESSED_DIR)

ensure_directories()

# Text Rendering Settings
TEXT_FONT_SIZE = 24 # Reduzido um pouco para caber melhor na moldura
TEXT_FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"
FRAME_PATH = "png/frame.png"

# Remote Status Config
REMOTE_SERVER_URL = os.getenv("REMOTE_SERVER_URL", "http://localhost:5001")

def update_remote_status(filename, status):
    try:
        url = f"{REMOTE_SERVER_URL}/status/{filename}"
        requests.post(url, json={"status": status})
        print(f"Status Remoto [{filename}]: {status}")
    except Exception as e:
        print(f"Erro ao atualizar status remoto: {e}")

def text_to_image(text, width=PRINTER_WIDTH):
    """
    Converts raw text to a 1-bit PIL image for the printer, overlaying it on a frame.
    """
    # 1. Carregar e preparar a moldura
    try:
        frame = Image.open(FRAME_PATH).convert("RGBA")
        # Redimensionar mantendo a proporção para a largura da impressora
        aspect = frame.height / frame.width
        frame_height = int(width * aspect)
        frame = frame.resize((width, frame_height), Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"Erro ao carregar moldura: {e}")
        # Fallback para fundo branco se a moldura falhar
        frame_height = 600 # Altura padrão se falhar
        frame = Image.new("RGBA", (width, frame_height), (255, 255, 255, 255))

    # 2. Definir área de texto (aproximada baseada na imagem Frame 1.png)
    # Logo no topo ~28%, Chapéu embaixo ~20%
    top_margin = int(frame_height * 0.28)
    bottom_margin = int(frame_height * 0.20)
    left_margin = 40
    right_margin = 40
    max_text_width = width - left_margin - right_margin
    max_text_height = frame_height - top_margin - bottom_margin

    # 3. Função auxiliar para testar quebra de linha com um dado tamanho de fonte
    def get_lines_for_font(f_size):
        try:
            font = ImageFont.truetype(TEXT_FONT_PATH, f_size)
        except:
            font = ImageFont.load_default()
            
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            if hasattr(font, 'getlength'):
                line_width = font.getlength(test_line)
            else:
                line_width = font.getsize(test_line)[0]
                
            if line_width < max_text_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        
        line_spacing = 4
        line_height = f_size + line_spacing
        total_height = len(lines) * line_height
        return lines, font, total_height, line_height

    # 4. Encontrar melhor tamanho de fonte (Escalonamento Dinâmico)
    best_font_size = 20 # Mínimo
    max_font_size = 60 # Máximo para não ficar bizarro
    
    # Busca linear regressiva para encontrar o maior tamanho que caiba na Moldura
    for s in range(max_font_size, best_font_size - 1, -2):
        lines, font, total_height, line_height = get_lines_for_font(s)
        if total_height <= max_text_height:
            best_font_size = s
            break
    
    # Rodar uma última vez com o melhor tamanho encontrado
    lines, font, total_height, line_height = get_lines_for_font(best_font_size)

    # 5. Desenhar o texto centralizado na moldura
    canvas = Image.new("RGBA", (width, frame_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # Centralizar verticalmente na área disponível
    y = top_margin + (max_text_height - total_height) // 2
    
    for line in lines:
        if hasattr(font, 'getlength'):
            text_w = font.getlength(line)
        else:
            text_w = font.getsize(line)[0]
        
        # Centralizar horizontalmente
        x = left_margin + (max_text_width - text_w) // 2
        draw.text((x, y), line, font=font, fill=(0, 0, 0, 255))
        y += line_height

    # 6. Combinar moldura e texto
    combined = Image.alpha_composite(frame, canvas)
    
    # Converter para 1-bit para a impressora
    # Usamos fundo branco para qualquer transparência restante
    final_img = Image.new("RGB", combined.size, (255, 255, 255))
    final_img.paste(combined, mask=combined.split()[3] if len(combined.split()) > 3 else None)
    
    return final_img.convert("1")

def process_image(img_input):
    """
    Takes a path or a PIL Image object and prepares it for the Phomemo T02.
    """
    if isinstance(img_input, str):
        img = Image.open(img_input)
    else:
        img = img_input
        
    # Resize keeping aspect ratio
    w_percent = (PRINTER_WIDTH / float(img.size[0]))
    h_size = int((float(img.size[1]) * float(w_percent)))
    img = img.resize((PRINTER_WIDTH, h_size), Image.Resampling.LANCZOS)
    
    # Convert to 1-bit
    img = img.convert("1")
    return img

def image_to_escpos(img):
    """
    Convert 1-bit PIL image to ESC/POS 'GS v 0' raster format.
    """
    WIDTH_BYTES = PRINTER_WIDTH // 8
    
    from PIL import ImageOps
    # Invert so white=0 (no burn), black=1 (burn)
    img = ImageOps.invert(img.convert("L")).convert("1")
    
    data = img.tobytes()
    commands = []
    
    # Init printer
    commands.append(b'\x1b\x40') 
    
    # Send image in chunks
    chunk_height = 100
    total_height = img.height
    
    for y in range(0, total_height, chunk_height):
        h = min(chunk_height, total_height - y)
        start = y * WIDTH_BYTES
        end = (y + h) * WIDTH_BYTES
        chunk_data = data[start:end]
        
        # Header for this chunk: GS v 0 0 xL xH yL yH
        xL = WIDTH_BYTES & 0xFF
        xH = (WIDTH_BYTES >> 8) & 0xFF
        yL = h & 0xFF
        yH = (h >> 8) & 0xFF
        
        cmd = b'\x1d\x76\x30\x00' + bytes([xL, xH, yL, yH]) + chunk_data
        commands.append(cmd)
        
    # Feed lines (footer)
    commands.append(b'\x1b\x64\x03')
    return commands

async def find_printer():
    """
    Robust printer discovery with user selection.
    """
    print("Buscando dispositivos Bluetooth (10s)...")
    scanned = await BleakScanner.discover(return_adv=True, timeout=10.0)
    found_devices = list(scanned.values())
    
    if not found_devices:
        return None

    # Filter likely candidates first
    candidates = []
    for d, a in found_devices:
        name = d.name or "Unknown"
        if "T02" in name or "Phomemo" in name:
            candidates.append(d)
    
    # If exactly one Phomemo found, return it
    if len(candidates) == 1:
        return candidates[0]
    
    # If none found by name or multiple, show list
    print("\n--- Dispositivos Bluetooth ---")
    for i, (device, adv) in enumerate(found_devices):
        name = device.name or "Unknown"
        marker = " [PROVÁVEL]" if device in candidates else ""
        print(f"{i}: {name}{marker} ({device.address}) | RSSI: {adv.rssi}")

    print("\nDigite o NÚMERO da impressora:")
    choice = input("Número >> ").strip()
    if choice.isdigit():
        idx = int(choice)
        if 0 <= idx < len(found_devices):
            return found_devices[idx][0]
    return None

class PhomemoPrinter:
    def __init__(self, device_or_address):
        self.target = device_or_address
        self.client = None
        self._lock = asyncio.Lock()
        self._status_event = asyncio.Event()
        self.last_status = {"ready": True, "msg": "Buscando..."}


    def _notification_handler(self, sender, data):
        if len(data) >= 3 and data[0] == 0x1a:
            raw_info = data[2]
            
            # Identificar se o Byte 2 são FLAGS
            if raw_info & 0x80:
                paper_present = bool(raw_info & 0x10)
                
                if not paper_present:
                    self.last_status["msg"] = "⚠️ Sem papel!"
                    self.last_status["ready"] = False
                else:
                    self.last_status["msg"] = "Pronta"
                    self.last_status["ready"] = True
            
            self._status_event.set()

    async def connect(self):
        if self.client and self.client.is_connected:
            return True
        
        print(f"Tentando conectar a {self.target}...")
        try:
            self.client = BleakClient(self.target)
            await self.client.connect()
            print(f"\u2705 Conectado com sucesso.")
            
            # Iniciar notificações imediatamente e manter abertas
            await self.client.start_notify(NOTIFY_CHARACTERISTIC_UUID, self._notification_handler)
            return True
        except Exception as e:
            print(f"\u274c Erro ao conectar: {e}")
            self.client = None
            return False

    async def ensure_connected(self):
        if not self.client or not self.client.is_connected:
            return await self.connect()
        return True

    async def check_status(self):
        """
        Attempts to read status from the printer using the persistent handler.
        """
        if not self.client or not self.client.is_connected:
            return False, "Desconectado"
            
        self._status_event.clear()
        try:
            # Solicitar status (0xAB 00 trigger Phomemo T02 STATUS packets)
            await self.client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, b'\xab\x00', response=False)
            
            # Esperar pela notificação que o handler persistente receberá
            try:
                await asyncio.wait_for(self._status_event.wait(), timeout=1.5)
            except asyncio.TimeoutError:
                # Se falhar, tenta o comando secundário GS g n
                await self.client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, b'\x1d\x67\x6e', response=False)
                try:
                    await asyncio.wait_for(self._status_event.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass
                
        except Exception as e:
            print(f"[ERRO Status] {e}")
            
        return self.last_status["ready"], self.last_status["msg"]

    async def print_image(self, image_src):
        """
        Main printing function. image_src can be path or PIL Image.
        """
        async with self._lock:
            if not await self.ensure_connected():
                return False

            print(f"Processando e enviando...")
            try:
                img = process_image(image_src)
            except Exception as e:
                print(f"Erro no processamento da imagem: {e}")
                return False

            commands = image_to_escpos(img)
            
            # 1. Check Status
            ready, msg = await self.check_status()
            if not ready:
                print(f"\n\u274c CANCELADO: {msg}")
                return False
            
            # 2. Print
            print(f"Status: {msg}. Enviando dados...")
            for i, cmd in enumerate(commands):
                await self.client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, cmd, response=False)
                await asyncio.sleep(0.04)
                if i % 10 == 0:
                    sys.stdout.write(f"\rProgresso: {int((i/len(commands))*100)}%")
                    sys.stdout.flush()
            
            print(f"\rProgresso: 100% - \u2705 Sucesso.")
            return True

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            self.client = None

async def process_file(printer, file_path):
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
        print(f"\nLido arquivo de imagem: {file_path}")
        return await printer.print_image(file_path)
    
    elif ext == '.txt':
        print(f"\nLido arquivo de texto: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        if not text:
            print("Arquivo de texto vazio. Ignorando.")
            return True
            
        img = text_to_image(text)
        return await printer.print_image(img)
    
    elif ext == '.pdf':
        if not fitz:
            print(f"Erro: PyMuPDF (fitz) não instalado. Não é possível imprimir PDF.")
            return False
            
        print(f"\nLido arquivo PDF: {file_path}")
        try:
            doc = fitz.open(file_path)
            for i, page in enumerate(doc):
                print(f"Pag {i+1}/{len(doc)}")
                pix = page.get_pixmap(dpi=203)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                success = await printer.print_image(img)
                if not success: return False
                if i < len(doc) - 1: await asyncio.sleep(2)
            return True
        except Exception as e:
            print(f"Erro processando PDF: {e}")
            return False
    
    return False

async def monitor_folder(printer):
    if not os.path.exists(WATCH_DIR): os.makedirs(WATCH_DIR)
    if not os.path.exists(PROCESSED_DIR): os.makedirs(PROCESSED_DIR)
    
    print(f"\n--- Iniciando Monitoramento (Polling) ---")
    print(f"Observando pasta: {os.path.abspath(WATCH_DIR)}")
    print(f"Pressione Ctrl+C para parar.\n")
    
    last_status_msg = None
    last_battery = None
    last_heartbeat = 0
    HEARTBEAT_INTERVAL = 1  # segundos (conforme alteração do usuário)
    FORCE_REPORT_INTERVAL = 30 # Forçar log a cada 30s mesmo se nada mudar
    
    while True:
        try:
            # 1. Garantir conexão
            is_connected = await printer.ensure_connected()
            if not is_connected:
                if last_status_msg != "Desconectado":
                    print(f"[{time.strftime('%H:%M:%S')}] \u274c Status: Desconectado")
                    last_status_msg = "Desconectado"
                await asyncio.sleep(2)
                continue

            # 2. Verificar Status para detecção de mudanças
            ready, msg = await printer.check_status()
            timestamp = time.strftime("%H:%M:%S")

            # Se houve mudança de status, ou se faz tempo que não reportamos
            status_changed = (msg != last_status_msg)
            time_to_heartbeat = (time.time() - last_heartbeat > FORCE_REPORT_INTERVAL)

            if status_changed or time_to_heartbeat:
                icon = "\u2705" if ready else "\u26a0\ufe0f"
                print(f"[{timestamp}] {icon} Status: {msg}")
                
                last_status_msg = msg
                last_heartbeat = time.time()

            # 3. Processar arquivos da fila
            files = [f for f in os.listdir(WATCH_DIR) if os.path.isfile(os.path.join(WATCH_DIR, f))]
            
            if files:
                for file_name in sorted(files):
                    if file_name.startswith('.'): continue
                    
                    file_path = os.path.join(WATCH_DIR, file_name)
                    success = await process_file(printer, file_path)
                    
                    if success:
                        try:
                            update_remote_status(file_name, "Pronto")
                            os.remove(file_path)
                            print(f"Limpeza: Arquivo {file_name} deletado da fila após impressão.")
                        except Exception as delete_err:
                            print(f"Erro ao deletar arquivo: {delete_err}")
                    else:
                        print(f"Falha ao imprimir {file_name}. Tentará novamente no próximo ciclo.")
            
        except Exception as e:
            print(f"Erro no monitor: {e}")
            await asyncio.sleep(2)
            
        await asyncio.sleep(HEARTBEAT_INTERVAL)

async def main():
    direct_address = os.getenv("BLE_PRINTER_ADDRESS")
    if direct_address:
        print(f"Usando endereço fixo do .env: {direct_address}")
        target = direct_address
    else:
        target = await find_printer()

    if not target:
        print("\n\u274c Nenhuma impressora selecionada ou encontrada.")
        return
        
    printer = PhomemoPrinter(target)
    
    if len(sys.argv) > 1:
        # Modo de comando único
        img_path = sys.argv[1]
        await printer.print_image(img_path)
        await printer.disconnect()
    else:
        # Modo monitoramento
        await monitor_folder(printer)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário.")
    except Exception as e:
        print(f"\nErro fatal: {e}")
