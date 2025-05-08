from direct.showbase.ShowBase import ShowBase
from panda3d.core import LPoint3
from core.engine import Engine
from core.scene_manager import SceneManager
from player.controller import PlayerController
from ui.hud import HUD

class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.engine = Engine(self)
        self.scene_manager = SceneManager(self)
        self.player_controller = PlayerController(self)
        self.hud = HUD(self)

        self.scene_manager.force_doors_open = False  # Porta começa visível
        self.scene_manager.load_first_room()

        self.taskMgr.add(self.update, "update")

    def update(self, task):
        # Verifica se jogador chegou perto da porta
        if self.scene_manager.door_node:
            player_pos = self.player_controller.actor.get_pos()
            door_pos = self.scene_manager.door_node.get_pos()
            dist = (player_pos.get_xz() - door_pos.get_xz()).length()

            if dist < 2.5 and not self.scene_manager.next_room_generated:
                self.scene_manager.next_room_generated = True
                self.scene_manager.load_room()

        # Pressionar espaço remove a porta (abre ela)
        if self.mouseWatcherNode.is_button_down('space'):
            self.scene_manager.abrir_porta()

        return task.cont


if __name__ == "__main__":
    from sys import platform
    import asyncio
    if platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    game = Game()
    game.run()
