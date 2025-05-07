from panda3d.core import NodePath

class SceneManager:
    def __init__(self, app):
        self.app = app
        self.current_room = None

    def load_first_room(self):
        if self.current_room:
            self.current_room.removeNode()
        self.current_room = NodePath("Room")
        self.current_room.reparentTo(self.app.render)
        # Aqui você adicionaria chão, paredes, NPC etc.
