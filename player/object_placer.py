from panda3d.core import Point3, Filename
from direct.task import Task
from direct.interval.IntervalGlobal import LerpHprInterval
import asyncio
import aiohttp

class ObjectPlacer:
    def __init__(self, app):
        self.app = app
        self.preview_node = None
        self.real_model = None
        self.placing = False
        self.task = None
        self.preview_rotation = None

    async def start_placement(self, prompt: str):
        self.placing = True

        # Carrega o placeholder .obj com textura embutida
        self.preview_node = self.app.loader.loadModel("assets/models/placeholder.obj")
        self.preview_node.setTransparency(True)
        self.preview_node.setColorScale(1.5, 1.5, 1.5, 0.5)
        self.preview_node.reparentTo(self.app.camera)
        self.preview_node.setPos(0, 5, -1)

        # Roda o preview
        self.preview_rotation = self.preview_node.hprInterval(2, (360, 0, 0))
        self.preview_rotation.loop()

        # Cria task que atualiza a posição do preview
        self.task = self.app.taskMgr.add(self._update_preview, "UpdatePreviewTask")

        # Inicia carregamento do modelo real
        asyncio.create_task(self._fetch_model(prompt))

    async def _fetch_model(self, prompt: str):
        job_id = await self._send_prompt(prompt)
        obj_url = await self._wait_for_obj(job_id)

        # Substitui o placeholder
        if self.preview_node:
            self.preview_node.removeNode()
        if self.preview_rotation:
            self.preview_rotation.finish()

        self.real_model = self.app.loader.loadModel(Filename.fromOsSpecific(obj_url))
        self.real_model.setTransparency(True)
        self.real_model.setColorScale(1.5, 1.5, 1.5, 0.5)
        self.real_model.reparentTo(self.app.camera)
        self.real_model.setPos(0, 5, -1)

    def _update_preview(self, task):
        if self.real_model:
            self.real_model.setPos(0, 5, -1)
        elif self.preview_node:
            self.preview_node.setPos(0, 5, -1)
        return Task.cont

    def confirm_placement(self):
        if not self.placing:
            return

        target = self._raycast_to_ground()
        if not target:
            return

        model = self.real_model or self.preview_node
        model.wrtReparentTo(self.app.render)
        model.setTransparency(False)
        model.setColorScale(1, 1, 1, 1)
        model.setPos(target)

        self._cleanup()

    def _cleanup(self):
        self.placing = False
        if self.task:
            self.app.taskMgr.remove(self.task)
        self.preview_node = None
        self.real_model = None
        if self.preview_rotation:
            self.preview_rotation.finish()
            self.preview_rotation = None

    def _raycast_to_ground(self):
        start = self.app.camera.getPos()
        dir = self.app.camera.getQuat().getForward()
        if dir.getZ() == 0:
            return None
        scale = -start.getZ() / dir.getZ()
        hit = start + dir * scale
        return Point3(hit.getX(), hit.getY(), 0)

    async def _send_prompt(self, prompt: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post("http://127.0.0.1:8000/generate", json={"prompt": prompt}) as resp:
                return (await resp.json())["job_id"]

    async def _wait_for_obj(self, job_id: str) -> str:
        for _ in range(100):
            await asyncio.sleep(0.1)
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://127.0.0.1:8000/result/{job_id}") as resp:
                    data = await resp.json()
                    if data["status"] == "finished":
                        return data["obj_url"]
        raise TimeoutError("Tempo de espera excedido para o modelo.")
