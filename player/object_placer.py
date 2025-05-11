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
        self.final_position = None

        self.temp_models = []  # <- modelos clonados da engrenagem


    async def start_placement(self, path: str = None, pos: Point3 = None, index_to_replace: int = None):
        print("▶️ Iniciando colocação do modelo")

        if path is not None and pos is not None:
            # Substitui engrenagem específica, se índice for fornecido
            if index_to_replace is not None and 0 <= index_to_replace < len(self.temp_models):
                node_to_remove = self.temp_models[index_to_replace]
                if node_to_remove:
                    node_to_remove.removeNode()
                    self.temp_models[index_to_replace] = None  # marca como removido

            model_node = self._load_model_preview(path)
            self._place_final_model(model_node, pos)
            self.placing = False
            return

        # Caso seja o placeholder inicial
        self._cleanup_preview()
        self.preview_node = self._load_model_preview("assets/models/placeholder.obj")
        self._start_preview_mode(self.preview_node)
        self.placing = True



    def confirm_placement(self) -> Point3 | None:
        print("🎯 Confirmando posicionamento...")

        if not self.preview_node:
            print("⚠️ Nenhum preview encontrado!")
            return None

        hit_pos = self._raycast_to_ground()
        if hit_pos:
            print("📍 Posicionando modelo em:", hit_pos)
            self.preview_node.setPos(hit_pos)
            self._align_model_to_ground(self.preview_node, hit_pos)
            self.preview_node.setColorScale(1, 1, 1, 1)
            self.preview_node.clearTransparency()
            self.preview_rotation.finish()
            self.placing = False

            self._create_persistent_model(self.preview_node)
            self._cleanup_preview()

            return hit_pos
        else:
            print("❌ Nenhum ponto válido encontrado para colocar o objeto.")
            return None


    def _create_persistent_model(self, source_node: NodePath):
        clone = source_node.copyTo(self.app.render)
        clone.setTransparency(False)
        clone.setColorScale(1, 1, 1, 1)
        clone.setPos(source_node.getPos())
        clone.setHpr(source_node.getHpr())
        clone.setScale(source_node.getScale())
        
        self.temp_models.append(clone)  # <- guardamos a engrenagem persistente
    
    def _load_model_preview(self, path: str) -> NodePath:
        model = self.app.loader.loadModel(str(path))
        self._normalize_scale(model)
        return model

    def _start_preview_mode(self, node: NodePath):
        node.reparentTo(self.app.render)
        node.setTransparency(True)
        node.setColorScale(1.5, 1.5, 1.5, 0.5)
        node.setPos(0, 5, -1)
        self.preview_rotation = node.hprInterval(2, (360, 0, 0))
        self.preview_rotation.loop()
        self.task = self.app.taskMgr.add(self._update_preview, "UpdatePreviewTask")

    def _place_final_model(self, node: NodePath, pos: Point3):
        self._cleanup_preview()
        node.reparentTo(self.app.render)
        node.setTransparency(False)
        node.setColorScale(1, 1, 1, 1)
        node.setPos(pos)
        self._align_model_to_ground(node, pos)
        self.placing = False

    def _cleanup_preview(self):
        if self.preview_node:
            self.preview_node.removeNode()
        if self.preview_rotation:
            self.preview_rotation.finish()
        self.preview_node = None
        self.preview_rotation = None
        if self.task:
            self.app.taskMgr.remove(self.task)
            self.task = None

    def _update_preview(self, task):
        if not self.placing or not self.preview_node:
            return Task.done
        if task.time < 0.2:
            return Task.cont

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
            self.preview_node.setPos(hit)
            self._align_model_to_ground(self.preview_node, hit)

        ray_path.removeNode()
        return Task.cont

    def _raycast_to_ground(self):
        ray = CollisionRay()
        ray.setOrigin(self.app.camera.getPos(self.app.render))
        ray.setDirection(self.app.camera.getQuat(self.app.render).getForward())

        cnode = CollisionNode('placement_ray')
        cnode.addSolid(ray)
        cnode.setFromCollideMask(BitMask32.bit(1))
        cnode.setIntoCollideMask(BitMask32.allOff())

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

    def _normalize_scale(self, node: NodePath, desired_size: float = 1.0):
        bounds = node.getTightBounds()
        if not bounds or bounds[0] is None or bounds[1] is None:
            return

        size_vec = bounds[1] - bounds[0]
        max_dimension = max(size_vec.getX(), size_vec.getY(), size_vec.getZ())
        if max_dimension == 0:
            return

        scale = desired_size / max_dimension
        node.setScale(scale)

    def _align_model_to_ground(self, node: NodePath, pos: Point3, overlap: float = 0.05):
        bounds = node.getTightBounds()
        if bounds and bounds[0] and bounds[1]:
            bottom = bounds[0].getZ()
            final_z = pos.getZ() - bottom - overlap
            node.setZ(final_z)

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
