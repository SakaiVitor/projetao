import asyncio, aiohttp, aiofiles, tempfile, uuid
from math import degrees, atan2
from pathlib import Path
from direct.task import Task
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import (NodePath, Filename, CollisionRay, CollisionNode, CollisionHandlerQueue,
                          CollisionTraverser, BitMask32, Point3)

API_URL = "http://127.0.0.1:8000"

class PendingObject:
    def __init__(self, app, prompt: str):
        self.app = app
        self.prompt = prompt
        self.placeholder = None
        self.final_model_path = None
        self.final_model_node = None
        self.progress_text = None
        self.rotation = None
        self.task = None
        self.ready = False
        self.placed = False
        self.position = None

    async def start(self):
        self.placeholder = self.app.loader.loadModel("assets/models/placeholder.obj")
        self._normalize_scale(self.placeholder)
        self.placeholder.reparentTo(self.app.render)
        self.placeholder.setTransparency(True)
        self.placeholder.setColorScale(1.5, 1.5, 1.5, 0.5)
        self.placeholder.setPos(0, 5, -1)
        self.rotation = self.placeholder.hprInterval(2, (360, 0, 0))
        self.rotation.loop()

        self.progress_text = OnscreenText(text="0%", pos=(0, 0.7), scale=0.07, fg=(1, 1, 1, 1))
        self.task = self.app.taskMgr.add(self.update_task, f"progress-task-{id(self)}")

        asyncio.create_task(self._request_and_download_obj())

    async def _request_and_download_obj(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_URL}/generate", json={"prompt": self.prompt}) as resp:
                job_id = (await resp.json())["job_id"]

        for _ in range(300):
            await asyncio.sleep(0.1)
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_URL}/result/{job_id}") as resp:
                    data = await resp.json()
                    if self.progress_text:
                        self.progress_text.setText(f"{data.get('progress', 0)}%")
                    if data["status"] == "finished":
                        path = await self._download_model(f"{API_URL}{data['obj']}")
                        self.final_model_path = path
                        self.ready = True
                        break

    async def _download_model(self, url: str) -> str:
        filename = Path(tempfile.gettempdir()) / f"{uuid.uuid4().hex}.obj"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                async with aiofiles.open(filename, "wb") as f:
                    await f.write(await resp.read())
        return str(filename)

    def update_task(self, task):
        if self.placed:
            return Task.cont

        model_to_move = self.final_model_node if self.final_model_node else self.placeholder
        if not model_to_move:
            return Task.done

        # Atualiza posição
        picker = CollisionTraverser()
        queue = CollisionHandlerQueue()
        ray = CollisionRay()
        ray.setFromLens(self.app.camNode, 0, 0)
        ray_node = CollisionNode('preview_ray')
        ray_node.addSolid(ray)
        ray_node.setFromCollideMask(BitMask32.bit(1))
        ray_path = self.app.camera.attachNewNode(ray_node)
        picker.addCollider(ray_path, queue)
        picker.traverse(self.app.render)

        if queue.getNumEntries() > 0:
            queue.sortEntries()
            hit = queue.getEntry(0).getSurfacePoint(self.app.render)
            model_to_move.setPos(hit)
            self._align_to_ground(model_to_move, hit)

        ray_path.removeNode()

        # Substitui engrenagem se pronto
        if self.ready and not self.final_model_node:
            pos = self.placeholder.getPos()
            self.placeholder.removeNode()
            self.rotation.finish()
            if self.progress_text:
                self.progress_text.setText("Pronto!")

            self.final_model_node = self.app.loader.loadModel(Filename.fromOsSpecific(self.final_model_path).getFullpath())
            self._normalize_scale(self.final_model_node)
            self.final_model_node.setTransparency(True)
            self.final_model_node.setColorScale(1.5, 1.5, 1.5, 0.5)
            self.final_model_node.reparentTo(self.app.render)
            self.final_model_node.setPos(pos)
            self.rotation = self.final_model_node.hprInterval(2, (360, 0, 0))
            self.rotation.loop()

        return Task.cont

    def confirm(self):
        if self.placed or not self.ready or not self.final_model_node:
            return

        hit = self._raycast_to_ground()
        if not hit:
            return

        self.final_model_node.setPos(hit)
        self._align_to_ground(self.final_model_node, hit)
        # Faz o objeto rotacionar para "olhar" para a câmera
        obj_pos = self.final_model_node.getPos(self.app.render)
        cam_pos = self.app.camera.getPos(self.app.render)

        # Direção da câmera em relação ao objeto no plano X/Y
        direction = (cam_pos - obj_pos)
        direction.setZ(0)  # ignora altura para rotação apenas no plano horizontal

        if direction.length_squared() > 0:
            direction.normalize()
            heading = degrees(atan2(direction.getX(), direction.getY()))
            self.final_model_node.setH(heading)

        self.final_model_node.setTransparency(False)
        self.final_model_node.setColorScale(1, 1, 1, 1)
        self.rotation.finish()
        if self.progress_text:
            self.progress_text.destroy()
        self.placed = True
        self.position = hit  # salva posição final

        # ------------ CHAMA O NPC MANAGER ------------
        self.app.scene_manager.npc_manager.try_prompt_nearby(
            self.prompt,
            self.position  # Point3 com X,Y,Z
        )

    def _normalize_scale(self, node: NodePath, desired_size: float = 2.5):
        bounds = node.getTightBounds()
        if not bounds or bounds[0] is None or bounds[1] is None:
            return
        size_vec = bounds[1] - bounds[0]
        max_dimension = max(size_vec.getX(), size_vec.getY(), size_vec.getZ())
        if max_dimension == 0:
            return
        scale = desired_size / max_dimension
        node.setScale(scale)

    def _align_to_ground(self, node: NodePath, pos: Point3, overlap: float = 0.05):
        bounds = node.getTightBounds()
        if bounds and bounds[0] and bounds[1]:
            bottom = bounds[0].getZ()
            final_z = pos.getZ() - bottom - overlap
            node.setZ(final_z)

    def _raycast_to_ground(self):
        ray = CollisionRay()
        ray.setOrigin(self.app.camera.getPos(self.app.render))
        ray.setDirection(self.app.camera.getQuat(self.app.render).getForward())
        cnode = CollisionNode('confirm_ray')
        cnode.addSolid(ray)
        cnode.setFromCollideMask(BitMask32.bit(1))
        ray_np = self.app.render.attachNewNode(cnode)
        handler = CollisionHandlerQueue()
        self.app.cTrav.addCollider(ray_np, handler)
        self.app.cTrav.traverse(self.app.render)
        self.app.cTrav.removeCollider(ray_np)
        ray_np.removeNode()
        if handler.getNumEntries() > 0:
            handler.sortEntries()
            return handler.getEntry(0).getSurfacePoint(self.app.render)
        return None
