from direct.showbase.ShowBase import ShowBase
from panda3d.core import LPoint3, LVector3f, CollisionTraverser
from core.engine import Engine
from core.scene_manager import SceneManager
from player.controller import PlayerController
from ui.hud import HUD
from prompt.prompt_manager import PromptManager
from player.object_placer import ObjectPlacer
import shutil
import os


class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.engine = Engine(self)
        self.scene_manager = SceneManager(self)
        self.player_controller = PlayerController(self)
        self.hud = HUD(self)
        self.placer = ObjectPlacer(self)  # instancia o colocador de objetos

        self.loop = asyncio.get_event_loop()
        self.taskMgr.add(self._poll_asyncio, "asyncioPump")

        self.scene_manager.force_doors_open = False
        self.scene_manager.load_first_room()

        self.prompt_manager = PromptManager()
        self.placer = ObjectPlacer(self)

        self.cTrav = CollisionTraverser()

        L = SceneManager.WALL_LEN
        self.entry_offsets = {
            "north": LVector3f(0, -L + 2, 0),
            "south": LVector3f(0, L - 2, 0),
            "east": LVector3f(-L + 2, 0, 0),
            "west": LVector3f(L - 2, 0, 0),
        }

        self.taskMgr.add(self.update, "update")

        # Eventos de interação com ObjectPlacer
        self.accept("mouse1", self.confirm_placement)

    def update(self, task):
        if self.scene_manager.door_node:
            player_pos = self.player_controller.node.getPos(self.render)
            door_world = self.scene_manager.door_node.getPos(self.render)
            dist = (player_pos.get_xz() - door_world.get_xz()).length()

            if dist < 2.5:
                prev_exit = self.scene_manager.exit_dir
                self.scene_manager.load_room()
                offset = self.entry_offsets.get(prev_exit, LVector3f(0, 0, 0))
                new_room_pos = self.scene_manager.current_room.getPos(self.render)
                target = new_room_pos + offset + LVector3f(0, 0, 1.0)

                print(f"[main.py - update] Carregando nova sala em: {new_room_pos}")
                print(f"[main.py - update] Jogador reposicionado para: {target}")

                self.player_controller.node.setPos(target)

        if self.mouseWatcherNode.is_button_down('space'):
            self.scene_manager.abrir_porta()

        return task.cont

    def _poll_asyncio(self, task):
        self.loop.stop()        # encerra o passo anterior
        self.loop.run_forever() # executa pendentes
        return task.cont

    def confirm_placement(self):
        self.placer.confirm_placement()

    def handle_prompt_submission(self, prompt: str):
        print("🎯 [Game] handle_prompt_submission com prompt:", prompt)

        async def async_flow(prompt_text: str):
            # 1. Inicia preview da engrenagem
            await self.placer.start_placement()

            # 2. Aguarda clique do jogador (detecta nova engrenagem)
            print("🕐 Aguardando posicionamento da engrenagem...")
            before = len(self.placer.temp_models)

            while len(self.placer.temp_models) == before:
                await asyncio.sleep(0.1)

            index = before  # ← posição específica da engrenagem associada a este prompt
            pos = self.placer.temp_models[index].getPos()

            # 3. Solicita modelo
            print("⚙️ [Game] Enviando prompt para gerar modelo...")
            obj_temp_path = await self.prompt_manager.request_model(prompt_text)
            print("📦 [Game] Modelo salvo em (temp):", obj_temp_path)

            final_path = os.path.join("assets", "tmp_models", f"{prompt_text[:10]}_mesh.obj")
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            shutil.copy(obj_temp_path, final_path)

            print("✅ [Game] Modelo copiado para:", final_path)

            # 4. Substitui a engrenagem correta pelo modelo final
            await self.placer.start_placement(path=final_path, pos=pos, index_to_replace=index)

        self.loop.create_task(async_flow(prompt))

if __name__ == "__main__":
    from sys import platform
    import asyncio
    if platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    game = Game()
    game.run()
