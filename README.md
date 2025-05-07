
# Estrutura Modular do Jogo - Labirinto com Enigmas

## Arquivos Principais

### main.py
- Inicia o Panda3D.
- Chama SceneManager para gerar a primeira sala.
- Cria instância do PlayerController e HUD.
- Roda o loop principal do Panda3D.

## Diretórios e Módulos

### /core/
- **engine.py**: Define resolução da tela, framerate, input global e controle de troca de salas.
- **scene_manager.py**: Proceduralmente gera salas, posiciona NPCs e porta de saída.

### /player/
- **controller.py**: Controla movimentação FPS e entrada de texto com ENTER.
- **object_placer.py**: Gerencia placeholder e posicionamento de objetos via clique.

### /prompt/
- **prompt_manager.py**: Envia prompt ao servidor, monitora retorno e carrega modelo.
- **quiz_system.py**: Avalia se o objeto colocado resolve o enigma atual via semântica.

### /npc/
- **npc_manager.py**: Gera modelo do NPC com animação e área de interação.

### /ui/
- **hud.py**: Interface de texto, mensagens de status e barra de carregamento.

### /assets/
- **models/**: Objetos gerados pelo servidor.
- **textures/**: Texturas usadas nos modelos e ambiente.
- **npcs/**: Modelos e animações dos NPCs.

### /utils/
- **semantic.py**: Função `compare_semantic(prompt, respostas_padrao) -> score` usando embeddings.

### /config/
- **settings.py**: Configurações gerais como seed, paths e parâmetros de jogo.

---
