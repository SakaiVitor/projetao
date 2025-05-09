# npc/npc_manager.py

from panda3d.core import NodePath, LVector3f, Filename
from direct.showbase.Loader import Loader

class NPCManager:
    def __init__(self, app):
        self.app = app
        self.npc_models = [
            "assets/models/npc1.obj"
        ]

    def spawn_npc(self, position: LVector3f) -> NodePath:
        model_path = Filename.from_os_specific(self.npc_models[0])
        npc = self.app.loader.loadModel(model_path)
        npc.setScale(1)
        npc.setPos(position)
        npc.reparentTo(self.app.render)
        return npc
