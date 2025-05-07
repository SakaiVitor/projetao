from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectEntry, OnscreenText
from direct.task.TaskManagerGlobal import taskMgr
from panda3d.core import Filename, ModelPool, TexturePool
import math, sys, asyncio

from prompt.prompt_manager import PromptManager

class OrbitViewer(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.disableMouse()

        self.status = OnscreenText("Digite um prompt e pressione ENTER", pos=(0, 0.9), scale=0.05)
        self.entry = DirectEntry(
            text="", scale=0.05, pos=(-0.9, 0, 0.8),
            command=self.on_submit, focus=1, suppressKeys=1,
            focusInCommand=lambda: self.entry.enterText("")
        )

        self.loop = asyncio.get_event_loop()
        taskMgr.add(self._poll_asyncio, "asyncio")

        self.model_node = None
        self.orbit_radius = 4
        self.orbit_speed = 360 / 10  # 1 volta a cada 10s
        taskMgr.add(self.auto_orbit, "cameraOrbit")

        self.prompt_manager = PromptManager()

    def _poll_asyncio(self, task):
        self.loop.stop()
        self.loop.run_forever()
        return task.cont

    def on_submit(self, text):
        prompt = text.strip()
        if not prompt:
            return
        self.status.setText(f"Enviando: {prompt}")
        self.loop.create_task(self.load_prompt_model(prompt))

    async def load_prompt_model(self, prompt: str):
        self.status.setText("Aguardando resposta do servidor...")
        try:
            obj_path = await self.prompt_manager.request_model(prompt)
        except Exception as e:
            self.status.setText(f"Erro: {e}")
            return

        self.status.setText("Carregando modelo...")

        if self.model_node:
            self.model_node.removeNode()
        ModelPool.releaseAllModels()
        TexturePool.releaseAllTextures()

        self.model_node = self.loader.loadModel(Filename.from_os_specific(str(obj_path)))
        self.model_node.reparentTo(self.render)
        self.model_node.setPos(0, 0, 0)

        self.camera.setPos(self.orbit_radius, 0, 0)
        self.camera.lookAt(0, 0, 0)
        self.status.setText("Modelo carregado. Câmera girando...")

    def auto_orbit(self, task):
        angle_deg = (task.time * self.orbit_speed) % 360
        angle_rad = math.radians(angle_deg)
        x = self.orbit_radius * math.cos(angle_rad)
        y = self.orbit_radius * math.sin(angle_rad)
        self.camera.setPos(x, y, 0)
        self.camera.lookAt(0, 0, 0)
        return task.cont


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    OrbitViewer().run()
