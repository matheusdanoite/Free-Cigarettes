# Histórico de Alterações (Changelog)

## [v1.5.0] - 15/02/2026
### Adicionado
- **Gerenciamento de Dependências**: Adição de `package.json` e configuração do Vite para o frontend.
- **Refinamento de Código**: Padronização de logs e tratamento de erros no `bridge.py` e `print_phomemo.py`.
- **Ajuste de Frontend**: Alinhando o frontend ao objetivo artístico do projeto.

### Alterado
- **Estrutura de Arquivos**: Organização de ativos em `barzar/assets/` e limpeza de arquivos temporários redundantes em `png/`.

## [v1.0.0] - 11/02/2026
- **Novo README**: Correção de umas burradas..

## [v1.0.0] - 11/02/2026
### Adicionado
- **Segurança e Privacidade**: Todas as configurações sensíveis (URLs, chaves) agora são carregadas de variáveis de ambiente (`.env`), eliminando dados hardcoded.
- **Portabilidade**: Scripts agora detectam automaticamente o diretório raiz do projeto, permitindo execução de qualquer local ou usuário via `start_barzar.sh`.
- **Configuração Simplificada**: Novo arquivo `.env.example` e documentação atualizada para facilitar o setup inicial.
- **Conexão Direta Phomemo**: Suporte opcional para `BLE_PRINTER_ADDRESS` no `.env` para pular o scan e conectar instantaneamente à impressora.
- **Correções de Robustez**: Scripts agora criam automaticamente pastas necessárias (`temp`, `uploads`, `png`) se não existirem, prevenindo crashes.

### Alterado
- **Caminhos Relativos**: Substituição completa de caminhos absolutos por relativos em todos os módulos (`server.py`, `bridge.py`, `start_barzar.sh`).
- **Frontend Configurável**: URL da API extraída para variável de configuração no topo do `index.html`.

## [v0.5.0] - 11/02/2026
### Adicionado
- **Sistema de Heartbeat**: Implementado um sinal de pulso a cada 30 segundos para manter a conexão Bluetooth ativa e evitar que a Phomemo T02 entre em modo de espera.
- **Sincronização de Status**: Mensagens de status "Pronto" e "Telepatia feita" agora são consistentes entre o bridge local e o servidor remoto.
- **Ancoragem de Overlays**: Refinamento da ancoragem do `cingarro.png` para alinhar precisamente com o landmark da boca.
- **Visualização de Tarefas**: Integração com gerenciamento de tarefas para melhor rastreamento do desenvolvimento.

## [v0.4.0] - 10/02/2026
### Adicionado
- **Fluxo Automatizado**: Criado o script `start_barzar.sh` para lançar Servidor, Túnel, Monitor de Impressora e Bridge em janelas separadas do terminal.
- **Escalonamento Dinâmico de Fonte**: Mensagens de texto agora ajustam o tamanho da fonte automaticamente para caber perfeitamente na moldura.

## [v0.3.0] - 10/02/2026
### Adicionado
- **Integração com Apple Vision**: Detecção de landmarks faciais implementada no `bridge.py` usando o framework nativo do macOS.
- **Overlays Dinâmicos**: Aplicação automática de itens aleatórios (óculos, brilhos, gatinhos, molduras) baseada nos pontos da face detectados e contraste do fundo.
- **Integração SIPS**: Otimização do processamento de imagem usando a ferramenta `sips` do macOS para garantir compatibilidade de DPI e formato.

## [v0.2.0] - 10/02/2026
### Adicionado
- **Arquitetura Híbrida**: Estabelecido o fluxo "Telepatia": Frontend (Web) -> Túnel Cloudflare -> Servidor Flask -> Bridge Local -> Impressora.
- **Túnel Cloudflare**: Comunicação segura entre o remoto e o local para o pipeline de impressão térmica.
- **Sistema de Polling**: Implementada lógica de busca de conteúdos pendentes no servidor remoto.

## [v0.1.0] - 09/02/2026
### Adicionado
- **Frontend Inicial**: Interface web responsiva para captura de fotos e envio de mensagens de texto.
- **Servidor Core**: Implementação básica em Flask para upload de arquivos e gerenciamento de status.
- **Logo e Identidade**: Ativos visuais para a identidade "Barzar".
