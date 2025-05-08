from direct.showbase.ShowBase import ShowBase
from panda3d.core import LPoint3, LVector3f
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

        L = SceneManager.WALL_LEN
        self.entry_offsets = {
            "north": LVector3f(0, -L + 2, 0),
            "south": LVector3f(0, L - 2, 0),
            "east": LVector3f(-L + 2, 0, 0),
            "west": LVector3f(L - 2, 0, 0),
        }

        self.taskMgr.add(self.update, "update")

    def update(self, task):
        if self.scene_manager.door_node:
            # distância XY entre player e porta
            player_pos = self.player_controller.node.getPos(self.render)
            door_world = self.scene_manager.door_node.getPos(self.render)
            # apenas XY
            dist = (player_pos.get_xz() - door_world.get_xz()).length()

            if dist < 2.5:
                # guarda a direção de saída da sala antiga
                prev_exit = self.scene_manager.exit_dir

                # carrega a próxima sala (N+1 vira atual)
                self.scene_manager.load_room()

                # reposiciona o jogador na entrada da nova sala
                offset = self.entry_offsets.get(prev_exit, LVector3f(0, 0, 0))
                new_room_pos = self.scene_manager.current_room.getPos(self.render)
                # sobe o player em Z para ficar acima do chão (+1m)
                target = new_room_pos + offset + LVector3f(0, 0, 1.0)

                print(f"[main.py - update] Carregando nova sala em: {new_room_pos}")
                print(f"[main.py - update] Jogador reposicionado para: {target}")

                self.player_controller.node.setPos(target)

        # abrir porta com espaço
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
