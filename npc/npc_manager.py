# npc/npc_manager.py

from panda3d.core import NodePath, LVector3f, Filename, TextNode
from direct.showbase.Loader import Loader
import random

class NPCManager:
    def __init__(self, app):
        self.app = app
        self.npc_models = [
            "assets/models/npc1.obj"
        ]
        self.speech_lines = [
            "Olá, viajante!",
            "Já enfrentou os desafios daqui?",
            "Use sua criatividade para seguir em frente.",
            "Essa sala tem algo especial...",
            "Você pode mudar tudo com palavras.",
        ]

    def spawn_npc(self, position: LVector3f) -> NodePath:
        model_path = Filename.from_os_specific(self.npc_models[0])
        npc = self.app.loader.loadModel(model_path)
        npc.setScale(1)
        npc.setPos(position)
        npc.reparentTo(self.app.render)

        speech_text = random.choice(self.speech_lines)
        speech = TextNode('npc-speech')
        speech.setText(speech_text)
        speech.setAlign(TextNode.ACenter)
        speech.setTextColor(1, 1, 1, 1)
        speech.setCardColor(0, 0, 0, 0.7)
        speech.setCardAsMargin(0.2, 0.2, 0.1, 0.1)

        speech_node = NodePath(speech.generate())
        speech_node.setScale(0.5)
        speech_node.setBillboardAxis()  
        speech_node.setPos(0, 0, 1)   
        speech_node.reparentTo(npc)
        return npc
