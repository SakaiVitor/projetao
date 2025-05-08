# npc/npc_manager.py

from panda3d.core import NodePath, LVector3f

class NPCManager:
    def __init__(self, app):
        self.app = app
        self.npc_models = [
            "models/misc/rgbCube"  # Placeholder até você ter um modelo de NPC real
        ]

    def spawn_npc(self, position: LVector3f) -> NodePath:
        model_path = self.npc_models[0]  # Pode randomizar depois se quiser
        npc = self.app.loader.loadModel(model_path)
        npc.setScale(1, 1, 2)
        npc.setPos(position)
        npc.setColor(1, 1, 0, 1)  # Amarelo para destacar
        return npc
