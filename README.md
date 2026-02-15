# Barzar Web: Cigarros Grátis
Barzar foi um encontro de arte, brechó e bebedeira. Também foi o vernissage do meu domínio. Para botar esse endereço web que acabei de adquirir para uso, decidi continuar um [projeto de engenharia reversa de uma impressora térmica Phomemo T02](https://github.com/matheusdanoite/Phomemo-T02-Driver-for-macOS). A ideia era permitir interações entre o digital e o físico, não sobrecarregar o usuário com conteúdo inútil, respeitar sua privacidade e também beber umas cervejas. O sistema permite que usuários enviem fotos e mensagens de uma interface web para serem processadas com filtros inteligentes via Apple Vision e impressas automaticamente na Phomemto T02 via Bluetooth.

## Como Funciona
Ao entrar no saity do Barzar, o usuário é recebido com duas escolhas: "Cigarros grátis", ou "Sou contra". 

A primeira escolha leva a uma visualização da câmera, que, uma vez capturada uma foto, é encaminhada via túnel da Cloudflare para o meu Mac, que faz o processamento via Apple Vision para detecção de faces, a inversão do arquivo de imagem de cigarro aplicado para otimizar o contraste com o fundo, envio dessas informações para a impressora e subsequente destruição de todos os arquivos processados.

Já na segunda escolha, o usuário tem a possibilidade de escrever um texto defendendo seu ponto de vista antitabagista, ou escrever o que lhe der na telha, dentro dos limites de 280 caracteres. O texto não passa pelo Vision Framework, mas tem um pipeline próprio que adapta o tamanho da fonte de acordo com o tamanho do conteúdo para melhor caber em uma dada área dentro de um arquivo de imagem para servir de moldura.

Ambos os modos possuem feedback de status em tempo real, informando o usuário de que passo está sendo realiado e com "Me perdi aqui" como mensagem de erro.

## Funcionalidades Principais
- **Captura Web**: Interface responsiva, otimizada para dispositivos mobile, capturando fotos e mensagens de texto.
- **Apple Vision Overlays**: Detecção de landmarks faciais para aplicação automática de cigarros e molduras.
- **Contraste Inteligente**: Inversão automática das cores dos overlays baseada no brilho da imagem de fundo para garantir visibilidade, visto que a Phomemo T02 imprime em escala de cinza com uma resolução baixíssima.
- **Dimensionamento de Texto**: Dimensionamento automático de texto para otimizar a ocupação de área possível de ser impressa.
- **Thermal Printing**: Driver customizado para Phomemo T02 [(disponível aqui no meu GitHub!)](https://github.com/matheusdanoite/Phomemo-T02-Driver-for-macOS) com suporte a imagens e textos.
- **Modo Telepatia**: Sincronização em tempo real do status da impressão (Mandando -> Telepatia feita -> Olhe a impressora -> Pronto).

## Arquitetura do Sistema
O projeto utiliza uma estrutura distribuída para contornar limitações de hardware e conectividade:
```mermaid
graph TD
    A[📱 Interface Web] -- "Upload (POST)" --> B[☁️ API Server / Flask]
    B -- "Polling / Files" --> C[🌉 Bridge Local / Python]
    C -- "Apple Vision / sips" --> D[🖼️ Processed Images]
    D -- "Local Queue" --> E[🖨️ Printer Monitor / BLE]
    E -- "ESC/POS Commands" --> F[📠 Phomemo T02]
    
    subgraph "Local macOS Machine"
    C
    D
    E
    end
```

## Stack Tecnológico
| Camada | Tecnologias |
| :--- | :--- |
| **Frontend** | HTML5, CSS3 (Vanilla), JavaScript, [Vite](https://vitejs.dev/) |
| **Backend** | Python, Flask, Flask-CORS |
| **Processing** | Apple Vision Framework, `pyobjc`, Pillow, `sips` |
| **Hardware/Comm** | Bluetooth LE, [Bleak](https://github.com/hbldh/bleak), Cloudflare Tunnels |

## Como Instalar e Rodar
### Pré-requisitos
- **macOS** (Obrigatório para Vision Framework e `sips`).
- **Python 3.10+**
- **Node.js 18+** (para o Frontend)
- **Bluetooth** habilitado.

### Configuração
1. **Clone o repositório**:
   ```bash
   git clone https://github.com/matheusdanoite/barzar-web.git
   cd barzar-web
   ```

2. **Ambiente Python**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
   
   Ou instale manualmente: 
   ```bash
   pip install flask flask-cors requests bleak Pillow pyobjc-framework-Vision pyobjc-framework-Quartz python-dotenv
   ```

3. **Ambiente Frontend**:
   ```bash
   npm install
   ```

4. **Configuração de API**:
    É necessário apontar o frontend para a URL correta da API.
    - Abra o arquivo [app.js](https://github.com/matheusdanoite/Cigarros-Gratis/blob/main/barzar/app.js).
    - Localize a linha 54 e substitua a URL em `const API_BASE_URL` pela sua URL do túnel ou IP local.

### Execução
Para facilitar, você pode usar o script de automação:
```bash
chmod +x start_barzar.sh
./start_barzar.sh
```
*Este script abrirá 4 terminais: Server, Tunnel, Printer Monitor e Bridge.*

Para rodar o **Frontend** em modo desenvolvimento:
```bash
npm run dev
```

## Dicas de Hardware (Phomemo T02)
- Certifique-se que a impressora está ligada e com carga.
- O sistema busca automaticamente o dispositivo via BLE. Se houver falha na conexão, verifique se nenhum outro app (como o oficial da Phomemo) está utilizando o Bluetooth.

## Créditos e Contribuições
- **Design & Arte**: Ana e Natan
- **Desenvolvimento**: [matheusdanoite](https://github.com/matheusdanoite).

> [!NOTE]
> Este projeto foi desenvolvido por puros fins artísticos e experimentais.

**Corporação matheusdanoite © 2026**
