from core.engine import Engine
from core.scene_manager import SceneManager
from player.controller import PlayerController
from ui.hud import HUD
from direct.showbase.ShowBase import ShowBase

class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.engine = Engine(self)
        self.scene_manager = SceneManager(self)
        self.player_controller = PlayerController(self)
        self.hud = HUD(self)

        self.scene_manager.load_first_room()

        self.taskMgr.add(self.update, "update")

    def update(self, task):
        self.player_controller.update()
        return task.cont

game = Game()
game.run()
