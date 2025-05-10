from panda3d.core import Point3, Filename, CardMaker, NodePath, CollisionRay, CollisionNode, CollisionHandlerQueue, BitMask32, CollisionTraverser

from direct.task import Task
from direct.interval.IntervalGlobal import LerpHprInterval
import asyncio
import aiohttp

API_URL = "http://127.0.0.1:8000"

class ObjectPlacer:
    def __init__(self, app):
        self.app = app
        self.preview_node = None
        self.real_model = None
        self.placing = False
        self.task = None
        self.preview_rotation = None

    async def start_placement(self, path: str = None):
        print("entrou aqui no start_placement")
        self.placing = True

        # Limpa preview anterior, se houver
        if self.preview_node:
            self.preview_node.removeNode()
            self.preview_node = None
        if self.preview_rotation:
            self.preview_rotation.finish()
            self.preview_rotation = None

        # Escolhe qual modelo carregar
        if path is None:
            path = "assets/models/placeholder.obj"

        # Carrega o modelo
        self._load_preview_model(path)

        # Cria task que atualiza a posição do preview
        self.task = self.app.taskMgr.add(self._update_preview, "UpdatePreviewTask")


    def _load_preview_model(self, path: str):
        self.preview_node = self.app.loader.loadModel(str(path))
        self._normalize_scale(self.preview_node, desired_size=1.0)  # ← aqui
        self.preview_node.setTransparency(True)
        self.preview_node.setColorScale(1.5, 1.5, 1.5, 0.5)
        self.preview_node.reparentTo(self.app.render)
        self.preview_node.setPos(0, 5, 0.5 if "placeholder" in path else -1)

        self.preview_rotation = self.preview_node.hprInterval(2, (360, 0, 0))
        self.preview_rotation.loop()


    async def _fetch_model(self, prompt: str):
        job_id = await self._send_prompt(prompt)
        obj_url = await self._wait_for_obj(job_id)

        # Substitui o placeholder
        if self.preview_node:
            self.preview_node.removeNode()
        if self.preview_rotation:
            self.preview_rotation.finish()

        self.real_model = self.app.loader.loadModel(Filename.fromOsSpecific(obj_url))
        self._normalize_scale(self.real_model, desired_size=1.0)
        self.real_model.setTransparency(True)
        self.real_model.setColorScale(1.5, 1.5, 1.5, 0.5)
        self.real_model.reparentTo(self.app.render)
        self.real_model.setPos(0, 5, -1)

    def confirm_placement(self):
        print("🎯 Confirmando posicionamento...")
        if not self.preview_node:
            print("⚠️ Nenhum preview encontrado!")
            return

        target = self._raycast_to_ground()
        if target:
            print("📍 Posicionando modelo em:", target)
            self.preview_node.setPos(target)
            self.preview_node.setColorScale(1, 1, 1, 1)
            self.preview_node.clearTransparency()
            self.preview_rotation.finish()
            self.placing = False
        else:
            print("❌ Nenhum ponto válido encontrado para colocar o objeto.")

    def _cleanup(self):
        self.placing = False
        if self.task:
            self.app.taskMgr.remove(self.task)
        self.preview_node = None
        self.real_model = None
        if self.preview_rotation:
            self.preview_rotation.finish()
            self.preview_rotation = None

    def _update_preview(self, task):
        if not self.placing or not self.preview_node:
            return Task.done

        if task.time < 0.2:  # Evita atualizar nos primeiros 0.2 segundos
            return Task.cont
        # Raycast a partir do centro da tela

        picker = CollisionTraverser()
        queue = CollisionHandlerQueue()

        # Raio da câmera para frente
        ray = CollisionRay()
        ray.setFromLens(self.app.camNode, 0, 0)  # centro da tela

        ray_node = CollisionNode('preview_ray')
        ray_node.addSolid(ray)
        ray_node.setFromCollideMask(BitMask32.bit(1))  # o chão precisa ter essa máscara
        ray_node_path = self.app.camera.attachNewNode(ray_node)

        picker.addCollider(ray_node_path, queue)
        picker.traverse(self.app.render)

        if queue.getNumEntries() > 0:
            queue.sortEntries()
            hit_pos = queue.getEntry(0).getSurfacePoint(self.app.render)
            self.preview_node.setPos(hit_pos)
            self.preview_node.setZ(hit_pos.getZ() + 0.05)  # levanta um pouco

        ray_node_path.removeNode()
        return Task.cont

    def _raycast_to_ground(self):
        # Cria ray do centro da câmera para frente
        ray = CollisionRay()
        ray.setOrigin(self.app.camera.getPos(self.app.render))
        ray.setDirection(self.app.camera.getQuat(self.app.render).getForward())

        cnode = CollisionNode('placement_ray')
        cnode.addSolid(ray)
        cnode.setFromCollideMask(BitMask32.bit(1))  # deve coincidir com o chão
        cnode.setIntoCollideMask(BitMask32.allOff())  # o ray não deve ser colidido

        ray_nodepath = self.app.render.attachNewNode(cnode)

        handler = CollisionHandlerQueue()
        self.app.cTrav.addCollider(ray_nodepath, handler)

        self.app.cTrav.traverse(self.app.render)
        self.app.cTrav.removeCollider(ray_nodepath)
        ray_nodepath.removeNode()

        if handler.getNumEntries() > 0:
            handler.sortEntries()
            point = handler.getEntry(0).getSurfacePoint(self.app.render)
            return point

        return None

    async def _send_prompt(self, prompt: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_URL}/generate", json={"prompt": prompt}) as resp:
                return (await resp.json())["job_id"]


    async def _wait_for_obj(self, job_id: str) -> str:
        for _ in range(100):
            await asyncio.sleep(0.1)
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_URL}/result/{job_id}") as resp:
                    data = await resp.json()
                    if data["status"] == "finished":
                        return f"{API_URL}{data['obj']}"
        raise TimeoutError("Tempo de espera excedido para o modelo.")
    
    def _normalize_scale(self, node: NodePath, desired_size: float = 1.0):
        bounds = node.getTightBounds()
        if not bounds or bounds[0] is None or bounds[1] is None:
            return

        size_vec = bounds[1] - bounds[0]
        max_dimension = max(size_vec.getX(), size_vec.getY(), size_vec.getZ())
        if max_dimension == 0:
            return

        scale_factor = desired_size / max_dimension
        node.setScale(scale_factor)