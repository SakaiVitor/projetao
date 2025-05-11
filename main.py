# main.py
from direct.showbase.ShowBase import ShowBase
from panda3d.core import LVector3f, CollisionTraverser, loadPrcFileData, CollisionHandlerPusher
from core.engine import Engine
from core.scene_manager import SceneManager
from player.controller import PlayerController
from ui.hud import HUD
from prompt.prompt_manager import PromptManager
from player.object_placer import ObjectPlacer
import asyncio

loadPrcFileData('', 'win-size 1600 900')
loadPrcFileData('', 'window-title PROJETAO')


class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # ───── Colisão ─────
        self.cTrav = CollisionTraverser()
        self.pusher = CollisionHandlerPusher()

        # sistemas centrais
        self.engine  = Engine(self)            # usado por outras partes do jogo
        self.scene_manager = SceneManager(self)
        self.player_controller = PlayerController(self)
        self.hud     = HUD(self)
        self.placer  = ObjectPlacer(self)
        self.prompt_manager = PromptManager()  # acessado dentro de ObjectPlacer / HUD

        self.loop = asyncio.get_event_loop()

        # primeira sala
        self.scene_manager.force_doors_open = False
        self.scene_manager.load_first_room()

        # tasks
        self.taskMgr.add(self.update, "update")
        self.taskMgr.add(self._poll_asyncio, "asyncioPump")

        # input
        self.accept("mouse1", self.placer.confirm_preview_under_cursor)
        self.accept("m", self.scene_manager.toggle_mapa_resumo)
        self.accept("M", self.scene_manager.toggle_mapa_resumo)

        self.cTrav.showCollisions(self.render)


    # ───────────── game-loop ─────────────
    def update(self, task):
        player_pos = self.player_controller.node.getPos(self.render)
        self.scene_manager.atualizar_sala_baseada_na_posicao(player_pos)

        if self.mouseWatcherNode.is_button_down('space'):
            self.scene_manager.abrir_porta()

        return task.cont

    def _poll_asyncio(self, task):
        # mantém o loop asyncio vivo sem bloquear o Panda3D
        self.loop.call_soon(self.loop.stop)
        self.loop.run_forever()
        return task.cont

    # camada de integração Prompt ↔ Placer
    def handle_prompt_submission(self, prompt: str):
        print("📨 [Game] Enviando prompt:", prompt)
        self.loop.create_task(self.placer.handle_prompt_submission(prompt))


if __name__ == "__main__":
    import sys
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    Game().run()
