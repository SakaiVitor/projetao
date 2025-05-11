from direct.showbase.ShowBase import ShowBase
from panda3d.core import LPoint3, LVector3f, CollisionTraverser
from core.engine import Engine
from core.scene_manager import SceneManager
from player.controller import PlayerController
from ui.hud import HUD
from prompt.prompt_manager import PromptManager
from player.object_placer import ObjectPlacer
import asyncio

class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.cTrav = CollisionTraverser()
        self.engine = Engine(self)
        self.scene_manager = SceneManager(self)
        self.player_controller = PlayerController(self)
        self.hud = HUD(self)
        self.placer = ObjectPlacer(self)
        self.prompt_manager = PromptManager()
        self.loop = asyncio.get_event_loop()

        self.cTrav = CollisionTraverser()

        self.scene_manager.force_doors_open = False
        self.scene_manager.load_first_room()

        L = SceneManager.WALL_LEN
        self.entry_offsets = {
            "north": LVector3f(0, -L + 2, 0),
            "south": LVector3f(0, L - 2, 0),
            "east": LVector3f(-L + 2, 0, 0),
            "west": LVector3f(L - 2, 0, 0),
        }

        self.taskMgr.add(self.update, "update")
        self.taskMgr.add(self._poll_asyncio, "asyncioPump")

        # clique para confirmar posicionamento
        self.accept("mouse1", self.confirm_placement)

        self.accept("m", self.scene_manager.toggle_mapa_resumo)
        self.accept("M", self.scene_manager.toggle_mapa_resumo)  # para o caso do Shift estar ativado


    def update(self, task):
        if self.scene_manager.door_node:
            player_pos = self.player_controller.node.getPos(self.render)
            door_world = self.scene_manager.door_node.getPos(self.render)
            dist = (player_pos.get_xz() - door_world.get_xz()).length()

            self.scene_manager.atualizar_sala_baseada_na_posicao(player_pos)


            # if dist < 2.5:
            #     prev_exit = self.scene_manager.exit_dir
            #     self.scene_manager.load_room()
            #     self.scene_manager.load_next_room()
            #     offset = self.entry_offsets.get(prev_exit, LVector3f(0, 0, 0))
            #     new_room_pos = self.scene_manager.current_room.getPos(self.render)
            #     target = new_room_pos + offset + LVector3f(0, 0, 1.0)

            #     print(f"[main.py - update] Carregando nova sala em: {new_room_pos}")
            #     print(f"[main.py - update] Jogador reposicionado para: {target}")

            #     self.player_controller.node.setPos(target)

        if self.mouseWatcherNode.is_button_down('space'):
            self.scene_manager.abrir_porta()

        return task.cont

    def _poll_asyncio(self, task):
        self.loop.stop()
        self.loop.run_forever()
        return task.cont

    def confirm_placement(self):
        self.placer.confirm_preview_under_cursor()

    def handle_prompt_submission(self, prompt: str):
        print("📨 [Game] Enviando prompt:", prompt)
        self.loop.create_task(self.placer.handle_prompt_submission(prompt))

if __name__ == "__main__":
    from sys import platform
    import asyncio
    if platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    game = Game()
    game.run()
