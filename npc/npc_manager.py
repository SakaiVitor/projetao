from panda3d.core import NodePath, LVector3f, Filename, TextNode
from pathlib import Path
from direct.task import Task
import random
from math import sin

class NPCManager:
    def __init__(self, app):
        self.app = app
        self.npc_dir = Path("assets/models/npcs")
        self.npc_models = list(self.npc_dir.glob("*.obj"))
        self.spawned_models = set()

        self.speech_lines = [
            "Olá, viajante!",
            "Já enfrentou os desafios daqui?",
            "Use sua criatividade para seguir em frente.",
            "Essa sala tem algo especial...",
            "Você pode mudar tudo com palavras.",
        ]

    def spawn_npc(self, position: LVector3f) -> NodePath:
        if not self.npc_models:
            print("Nenhum modelo .obj encontrado em assets/models/npcs")
            return None

        available_models = [m for m in self.npc_models if m not in self.spawned_models]
        if not available_models:
            self.spawned_models.clear()
            available_models = list(self.npc_models)

        model_path = random.choice(available_models)
        self.spawned_models.add(model_path)

        # Carrega o modelo
        npc = self.app.loader.loadModel(Filename.from_os_specific(str(model_path)))
        npc.setScale(2)
        npc.setPos(position)
        npc.reparentTo(self.app.render)

        # Alinha ao chão com leve sobreposição
        min_bound, max_bound = npc.getTightBounds()
        if min_bound and max_bound:
            npc.setZ(position.getZ() - min_bound.getZ() - 0.05)

        # Animação de respiração
        def breathing_task(task, node=npc):
            scale = 2 + 0.02 * sin(task.time * 2)
            node.setScale(scale)
            return Task.cont

        self.app.taskMgr.add(breathing_task, f"breathing-task-{id(npc)}")

        # Cria texto flutuante
        speech_text = random.choice(self.speech_lines)
        speech_node_text = TextNode("npc-text")
        speech_node_text.setText(speech_text)
        speech_node_text.setAlign(TextNode.ACenter)
        speech_node_text.setTextColor(1, 1, 1, 1)
        speech_node_text.setCardColor(0, 0, 0, 1)
        speech_node_text.setCardAsMargin(0.3, 0.3, 0.2, 0.2)
        speech_node_path = NodePath(speech_node_text.generate())
        speech_node_path.setScale(0.2)
        speech_node_path.setBillboardAxis()
        speech_node_path.setLightOff()
        speech_node_path.setDepthWrite(False)
        speech_node_path.setDepthTest(False)
        speech_node_path.reparentTo(self.app.render)

        speech_node_path.hide()  # ← começa invisível

        # Atualiza posição e visibilidade com base na distância
        def update_speech(task, npc=npc, node=speech_node_path):
            if not npc or not node:
                return Task.done

            node.setPos(npc.getX(), npc.getY(), npc.getZ() + 1)

            player_node = getattr(self.app.player_controller, "node", None)
            if player_node:
                distance = (npc.getPos(self.app.render) - player_node.getPos(self.app.render)).length()
                if distance < 10.0:
                    node.show()
                else:
                    node.hide()

            return Task.cont

        self.app.taskMgr.add(update_speech, f"text-follow-{id(npc)}")

        return npc
