# scene_manager.py
from pathlib import Path
import random
from math import sin, degrees, atan2
from glob import glob

from direct.interval.LerpInterval import LerpHprInterval
from panda3d.core import (
    NodePath, LVector3f, CardMaker, CollisionNode, CollisionBox, Point3, Vec3,
    CollisionPlane, BitMask32, Plane, TextureStage, TexGenAttrib, TransformState,
    LMatrix4f, LVecBase3f, TextNode, Filename, Texture
)

from direct.gui.OnscreenText import OnscreenText
from direct.task import Task

from core.load_wrapper import load_model_with_default_material
from npc.npc_manager import NPCManager


class SceneManager:
    # ─────────────── CONSTANTES DE SALA ────────────────
    CELL      = 20      # distância entre salas (grade)
    WALL_LEN  = 10      # meia-largura da sala
    WALL_ALT  = 5       # altura da parede
    WALL_THK  = 2       # espessura da parede
    DOOR_W    = 2       # largura da abertura da porta
    DOOR_THK  = .4      # profundidade da porta (porta fina)

    # ───────────────────── INIT ────────────────────────
    def __init__(self, app):
        self.app = app

        self.room_index     = 0
        self.current_room: NodePath | None = None
        self.next_room   : NodePath | None = None
        self.door_node   : NodePath | None = None
        self.exit_dir    : str | None      = None      # ‘north’ | ‘south’ | …

        self.rooms            : list[NodePath]   = []
        self.room_positions   : list[LVector3f]  = [LVector3f(0, 0, 0)]
        self.room_grid_set    : set[tuple[int,int]] = set()   # p/ colisão de grade

        self._mapa_visivel = False
        self._mapa_textos  : list[OnscreenText] = []
        self._limpeza_feita = False

        self.npc_manager   = NPCManager(app)
        self.floor_textures = glob("assets/textures/floor/*.jpg") + glob("assets/textures/floor/*.png")
        self.wall_textures = glob("assets/textures/walls/*.jpg") + glob("assets/textures/walls/*.png")
        self.ceiling_textures = glob("assets/textures/ceiling/*.jpg") + glob("assets/textures/ceiling/*.png")

    # ───────────────────────── PUBLIC ─────────────────────────
    def load_first_room(self) -> None:
        """
        Cria 5 salas.
        • A primeira tem saída fixa **Norte**.
        • As seguintes seguem a lógica aleatória, sem sobrepor posições.
        """
        current_pos = LVector3f(0, 0, 0)
        self.room_grid_set = {self._vec_to_tuple(current_pos)}

        prev_exit_dir = "north"                 # saída fixa da 1ª sala
        for i in range(6):                      # TOTAL = 5
            room = NodePath(f"Room-{i}")
            room.setPos(current_pos)

            if i == 0:
                # 1ª sala não tem entrada; força saída Norte
                self._build_room_contents(room, entry_dir=None,
                                           force_exit_dir="north",
                                           is_first=True)
            else:
                entry_dir = self._opposite(prev_exit_dir)
                self._build_room_contents(room,
                                           entry_dir=entry_dir,
                                           is_first=False)

            self.rooms.append(room)
            self.room_positions.append(current_pos)

            prev_exit_dir = self.exit_dir
            next_pos = current_pos + self._direction_to_offset(prev_exit_dir)

            # evita sobreposição na grade
            tried_dirs = {prev_exit_dir}
            while self._vec_to_tuple(next_pos) in self.room_grid_set:
                available = [d for d in ("north", "south", "east", "west")
                             if d not in tried_dirs]
                if not available:
                    break
                prev_exit_dir = random.choice(available)
                tried_dirs.add(prev_exit_dir)
                next_pos = current_pos + self._direction_to_offset(prev_exit_dir)

            current_pos = next_pos
            self.room_grid_set.add(self._vec_to_tuple(current_pos))

        # faz parents no render
        for room in self.rooms:
            room.reparentTo(self.app.render)
        self.current_room = self.rooms[0]

        print("\n🧱 [DEBUG] Estrutura da cena após criar todas as salas:")

    def load_next_room(self) -> None:
        if self.room_index + 1 < len(self.rooms):
            self.load_room(self.room_index + 1)
        else:
            print("[SceneManager] Fim das salas.")

    def load_room(self, index: int) -> None:
        if 0 <= index < len(self.rooms):
            if self.current_room:
                self.current_room.detachNode()

            self.current_room = self.rooms[index]
            self.current_room.reparentTo(self.app.render)
            self.room_index = index

            if self._mapa_visivel and self._mapa_textos:
                self.atualizar_sala_atual_no_mapa()

    # ───────────────────── BUILD DE SALA ─────────────────────
    def _build_room_contents(
            self,
            parent: NodePath,
            entry_dir: str | None,
            force_exit_dir: str | None = None,
            is_first: bool = False
    ) -> None:
        parent.setTag("wall_texture", random.choice(self.wall_textures))
        parent.setTag("floor_texture", random.choice(self.floor_textures))
        parent.setTag("ceiling_texture", random.choice(self.ceiling_textures))

        self._generate_floor(parent)
        self._generate_ceiling(parent)
        self._generate_walls_and_doors(parent, entry_dir, force_exit_dir, is_first)

        self._scatter_decor(parent, entry_dir)

    # ──────────── ESTRUTURAS: CHÃO / TETO ─────────────
    def _generate_floor(self, parent: NodePath) -> None:
        cm = CardMaker("floor")
        cm.setFrame(-self.WALL_LEN, self.WALL_LEN, -self.WALL_LEN, self.WALL_LEN)
        floor_vis = parent.attachNewNode(cm.generate())
        floor_vis.setHpr(0, -90, 0)
        floor_vis.setZ(0)

        tex_path = parent.getTag("floor_texture")
        self._apply_texture(floor_vis, tex_path)

        plane = Plane(Vec3(0, 0, 1), Point3(0, 0, 0))
        cnode = CollisionNode("floor_collision")
        cnode.addSolid(CollisionPlane(plane))
        cnode.setIntoCollideMask(BitMask32.bit(1))
        parent.attachNewNode(cnode).setZ(0)

    def _generate_ceiling(self, parent: NodePath) -> None:
        cm = CardMaker("ceiling")
        cm.setFrame(-self.WALL_LEN, self.WALL_LEN, -self.WALL_LEN, self.WALL_LEN)
        ceiling = parent.attachNewNode(cm.generate())
        ceiling.setPos(0, 0, self.WALL_ALT)
        ceiling.setHpr(0, 90, 0)

        tex_path = parent.getTag("ceiling_texture")
        self._apply_texture(ceiling, tex_path)

    # ────────── PAREDES / PORTAS ──────────
    def _generate_walls_and_doors(
            self,
            parent: NodePath,
            entry_dir: str | None,
            force_exit_dir: str | None,
            is_first: bool
    ) -> None:
        dirs = ["north", "south", "east", "west"]

        if is_first and force_exit_dir:
            self.exit_dir = force_exit_dir
            exit_door_node = None
            door_dirs = {force_exit_dir}

            # Cria apenas a parede com porta na direção da saída
            for d in dirs:
                if d == self.exit_dir:
                    self._create_wall_with_door(parent, d)
                    exit_door_node = self._create_door_only(parent, d)
                else:
                    self._create_wall(parent, d)

            self._spawn_npc(parent, entry_dir=None, door_node=exit_door_node)

        else:
            # Exclui entrada e direções que já possuem salas
            remaining = [
                d for d in dirs
                if d != entry_dir and
                   self._vec_to_tuple(parent.getPos() + self._direction_to_offset(d)) not in self.room_grid_set
            ]

            if not remaining:
                print(f"⚠️ [SceneManager] Sem saída válida na sala {self.room_index}")
                self.exit_dir = None
                exit_door_node = None

                # Cria somente a entrada
                for d in dirs:
                    if d == entry_dir:
                        self._create_wall_with_door(parent, d)
                    else:
                        self._create_wall(parent, d)

                self._spawn_npc(parent, entry_dir=entry_dir, door_node=None)
                return

            door_dirs = [entry_dir] if entry_dir else []
            self.exit_dir = random.choice(remaining)
            door_dirs.append(self.exit_dir)
            exit_door_node = None

            for d in dirs:
                if d in door_dirs:
                    self._create_wall_with_door(parent, d)
                    if d == self.exit_dir:
                        exit_door_node = self._create_door_only(parent, d)
                else:
                    self._create_wall(parent, d)

            self._spawn_npc(parent, entry_dir=entry_dir, door_node=exit_door_node)


    def _create_wall_with_door(self, parent: NodePath, d: str) -> None:
        """Parede dividida em 2 blocos com abertura no centro."""
        is_horizontal = d in ("north", "south")
        wall_z = self.WALL_ALT / 2
        door_half = self.DOOR_W / 2
        frame_half = self.WALL_LEN - door_half      # metade de cada batente

        for side in (-1, 1):
            piece = self.app.loader.loadModel("models/misc/rgbCube")
            if is_horizontal:
                piece.setScale(frame_half, self.WALL_THK, self.WALL_ALT + .5)
                x = side * (self.WALL_LEN - frame_half / 2)
                pos = (x,
                    self.WALL_LEN + self.WALL_THK / 2 if d == "north"
                    else -self.WALL_LEN - self.WALL_THK / 2,
                    wall_z)
            else:
                piece.setScale(self.WALL_THK, frame_half, self.WALL_ALT + .5)
                y = side * (self.WALL_LEN - frame_half / 2)
                pos = (
                    self.WALL_LEN + self.WALL_THK / 2 if d == "east"
                    else -self.WALL_LEN - self.WALL_THK / 2,
                    y, wall_z)

            piece.setPos(*pos)
            self._apply_room_texture(parent, piece)
            piece.reparentTo(parent)

            self._apply_room_texture(parent, piece)
            piece.reparentTo(parent)
            piece.setTexScale(TextureStage.getDefault(), 1, 1)

            # ── Collider corretamente centralizado ──
            scale = piece.getScale()
            half_x, half_y, half_z = scale.x / 8, scale.y / 8, scale.z
            box = CollisionBox((0, 0, 0), 0.5, 0.5, half_z)

            node = CollisionNode(f"wall-col-{d}-{side}")
            node.addSolid(box)
            node.setFromCollideMask(BitMask32.bit(1))
            piece.attachNewNode(node)

            # col_np = piece.attachNewNode(CollisionNode(f"wall-col-{d}-{side}"))
            # col_np.node.addSolid(box)
            # col_np.node.setIntoCollideMask(BitMask32.bit(1))

    def _create_door_only(self, parent: NodePath, d: str) -> NodePath:
        door = self.app.loader.loadModel("assets/models/porta.obj")
        door.setName(f"porta_sala_{self.room_index}_{d}")

        pos_map = {
            "north": (0, self.WALL_LEN + self.DOOR_THK / 2, self.WALL_ALT / 2),
            "south": (0, -self.WALL_LEN - self.DOOR_THK / 2, self.WALL_ALT / 2),
            "east": (self.WALL_LEN + self.DOOR_THK / 2, 0, self.WALL_ALT / 2),
            "west": (-self.WALL_LEN - self.DOOR_THK / 2, 0, self.WALL_ALT / 2),
        }

        DOOR_VISIBLE_WIDTH = 6

        if d in ("north", "south"):
            door.setScale(DOOR_VISIBLE_WIDTH, self.DOOR_THK, self.WALL_ALT + .5)
        else:
            door.setScale(self.DOOR_THK, DOOR_VISIBLE_WIDTH, self.WALL_ALT + .5)

        offset_fix = {
            "east": LVector3f(0, -0.45, 0),
            "west": LVector3f(0, -0.45, 0),
        }.get(d, LVector3f(0, 0, 0))

        final_pos = LVector3f(*pos_map[d]) + offset_fix
        door.setPos(final_pos)
        door.reparentTo(parent)

        # 🎯 Colisor baseado na escala atual
        scale = door.getScale()
        box = CollisionBox((0, 0, 0), 3, 3, scale.z / 2)
        col_node = CollisionNode(f"col-door-{self.room_index}-{d}")
        col_node.addSolid(box)
        col_node.setIntoCollideMask(BitMask32.bit(1))  # mesma máscara das paredes
        door.attachNewNode(col_node)

        if d == self.exit_dir:
            self.door_node = door
            parent.setPythonTag("door_node", door)

        return door

    def _create_wall(self, parent: NodePath, d: str) -> None:
        """Parede sólida completa."""
        wall = self.app.loader.loadModel("models/misc/rgbCube")

        positions = {
            "north": (0,  self.WALL_LEN + self.WALL_THK/2, self.WALL_ALT/2),
            "south": (0, -self.WALL_LEN - self.WALL_THK/2, self.WALL_ALT/2),
            "east":  ( self.WALL_LEN + self.WALL_THK/2, 0, self.WALL_ALT/2),
            "west":  (-self.WALL_LEN - self.WALL_THK/2, 0, self.WALL_ALT/2),
        }
        wall.setPos(*positions[d])

        if d in ("north", "south"):
            wall.setScale(self.CELL, self.WALL_THK, self.WALL_ALT)
            box = CollisionBox((0, 0, 0),
                               0.5, self.WALL_THK/2, self.WALL_ALT/2)
        else:
            wall.setScale(self.WALL_THK, self.CELL, self.WALL_ALT)
            box = CollisionBox((0, 0, 0),
                               self.WALL_THK/2, 0.5, self.WALL_ALT/2)

        self._apply_room_texture(parent, wall)
        wall.reparentTo(parent)

        self._apply_room_texture(parent, wall)
        wall.reparentTo(parent)
        wall.setTexScale(TextureStage.getDefault(), 1, 1)

        wall_cnode = CollisionNode(f"wall-col-{d}")
        wall_cnode.addSolid(box)
        wall_cnode.setIntoCollideMask(BitMask32.bit(1))
        wall.attachNewNode(wall_cnode)

        # col_np = wall.attachNewNode(CollisionNode(f"wall-col-{d}"))
        # col_np.node().addSolid(box)
        # col_np.node().setIntoCollideMask(BitMask32.bit(1))

    # ───────────── SPAWN DE NPC ─────────────
    def _spawn_npc(self, parent: NodePath, entry_dir: str | None, door_node: NodePath | None) -> None:
        if not self.exit_dir or door_node is None:
            return

        porta_pos = door_node.getPos(parent)
        dir_vec = (porta_pos - LVector3f(0, 0, 0)).normalized()
        perp_vec = LVector3f(-dir_vec.getY(), dir_vec.getX(), 0)

        npc_pos = porta_pos - dir_vec * 3.5 + perp_vec * 3.5

        npc_scale = 3.0
        npc = self.npc_manager.spawn_npc(door_node=door_node, npc_scale=npc_scale)
        npc.reparentTo(parent)
        npc.setPos(npc_pos)

        self.app.graphicsEngine.renderFrame()

        model_node = npc.find("**/model_node")
        if not model_node.isEmpty():
            min_bound, max_bound = model_node.getTightBounds()
            scale_z = model_node.getScale().getZ()

            if min_bound and max_bound:
                altura_modelo = (max_bound.getZ() - min_bound.getZ()) * scale_z
                centro_z_local = (min_bound.getZ() + max_bound.getZ()) / 2 * scale_z
                # move o modelo para que a base fique no chão
                npc.setZ(npc.getZ() - centro_z_local - altura_modelo / 2 + 0.1)

            speech_node = npc.find("**/speech_node")
            if not speech_node.isEmpty():
                speech_node.setZ(altura_modelo + 1)

        heading_deg = degrees(atan2(-dir_vec.getY(), -dir_vec.getX()))
        npc.setH(heading_deg)

    # ──────────── DECORAÇÃO ────────────
    def _scatter_decor(self, parent: NodePath, entry_dir: str | None) -> None:
        blocked = {self.exit_dir}
        if entry_dir:
            blocked.add(entry_dir)
        decor_dirs = [d for d in ("north", "south", "west", "east") if d not in blocked]

        pos_map = {
            "north": (0, self.WALL_LEN - 1.2, 0),
            "south": (0, -self.WALL_LEN + 1.2, 0),
            "west": (-self.WALL_LEN + 1.2, 0, 0),
            "east": (self.WALL_LEN - 1.2, 0, 0),
        }

        obj_dir = Path("assets/models/objects")
        obj_paths = list(obj_dir.glob("*.obj"))
        if not obj_paths:
            print("[SceneManager] Nenhum .obj em assets/models/objects")
            return

        placed: list[LVector3f] = []

        for d in decor_dirs:
            base_x, base_y, base_z = pos_map[d]
            dir_vec = LVector3f(-base_x, -base_y, 0).normalized()

            for _ in range(random.randint(1, 3)):
                model_path = random.choice(obj_paths)

                for _attempt in range(10):
                    offset = random.uniform(-2.5, 2.5)
                    pos = (LVector3f(base_x + offset, base_y, base_z + .2)
                           if d in ("north", "south")
                           else LVector3f(base_x, base_y + offset, base_z + .2))

                    # Afastar da parede em 1 unidade na direção oposta
                    pos += dir_vec * 1.0

                    if all((pos - p).length() >= 1.5 for p in placed):
                        model = load_model_with_default_material(self.app.loader, str(model_path))
                        model.setPos(pos)
                        model.setScale(random.uniform(2.2, 3.2))

                        heading = degrees(atan2(dir_vec.getY(), dir_vec.getX()))
                        model.setH(heading)

                        min_bound, _ = model.getTightBounds()
                        if min_bound:
                            model.setZ(model.getZ() - min_bound.getZ() - .05)

                        model.reparentTo(parent)
                        placed.append(pos)
                        break

    # ────────────── TEXTURAS ──────────────
    def _apply_room_texture(self, room: NodePath, node: NodePath) -> None:
        tex_path = room.getTag("wall_texture")
        self._apply_texture(node, tex_path)

    def _apply_texture(self, node: NodePath, texture_path: str) -> None:
        texture = self.app.loader.loadTexture(texture_path)

        node.setColor(1, 1, 1, 1)
        ts = TextureStage.getDefault()
        node.setTexture(ts, texture)
        node.setTexGen(ts, TexGenAttrib.MWorldPosition)

        scale_x, scale_y = .2, .4
        rotation = LMatrix4f.rotateMat(90, LVecBase3f(0, 0, 1))
        scale_mat = LMatrix4f.scaleMat(scale_x, scale_y, 1)
        matrix = rotation * scale_mat
        node.setTexTransform(ts, TransformState.makeMat(matrix))

    def _apply_random_texture(self, node: NodePath) -> None:
        texture = self.app.loader.loadTexture(random.choice(self.textures))
        node.setTexture(texture, 1)

    # ────────────── MAPA RESUMO ──────────────
    def gerar_mapa_resumo(self) -> None:
        center_x, center_y = .7, .7
        scale, offset = .05, .06
        min_x = min(p.getX() for p in self.room_positions)
        min_y = min(p.getY() for p in self.room_positions)

        self._mapa_textos = []
        for i, pos in enumerate(self.room_positions):
            grid_x = int((pos.getX() - min_x) / self.CELL)
            grid_y = int((pos.getY() - min_y) / self.CELL)
            text = OnscreenText(
                text=str(i),
                pos=(center_x - offset*grid_x, center_y - offset*grid_y),
                scale=scale, align=TextNode.ACenter, mayChange=True,
                fg=(1,1,1,1),
                bg=(1,0,0,.7) if i == self.room_index else (0,0,0,.6)
            )
            self._mapa_textos.append(text)
        self._mapa_visivel = True

    def esconder_mapa_resumo(self) -> None:
        for t in self._mapa_textos:
            t.destroy()
        self._mapa_textos = []
        self._mapa_visivel = False

    def toggle_mapa_resumo(self) -> None:
        if self._mapa_visivel:
            self.esconder_mapa_resumo()
        else:
            self.gerar_mapa_resumo()

    def atualizar_sala_atual_no_mapa(self) -> None:
        for i, t in enumerate(self._mapa_textos):
            if t is None:
                continue
            t.setBg((1,0,0,.7) if i == self.room_index else (0,0,0,.6))
        if i == len(self.rooms) - 1 and not self._limpeza_feita:
            self._limpeza_feita = True
            print("[SceneManager] Limpando salas anteriores...")
            for sala in self.rooms[:-1]:
                sala.detachNode()

    def atualizar_sala_baseada_na_posicao(self, player_pos: LVector3f) -> None:
        for i, sala_pos in enumerate(self.room_positions):
            if (abs(player_pos.getX() - sala_pos.getX()) <= self.CELL / 2 and
                    abs(player_pos.getY() - sala_pos.getY()) <= self.CELL / 2):

                if self.room_index != i:
                    self.room_index = i

                    # Mostra no mapa, se visível
                    if self._mapa_visivel:
                        self.atualizar_sala_atual_no_mapa()

                    # Verifica se entrou na Sala Final
                    if i == len(self.rooms) - 1 and not self._limpeza_feita:
                        self._limpeza_feita = True
                        print("[SceneManager] Entrou na Sala Final. Limpando tudo...")
                        self._criar_sala_final()  # ⬅️ Adicione aqui!

                        for sala in self.rooms:
                            if sala != self.sala_final_node:
                                sala.removeNode()

                return

    # ─────────────── HELPERS ───────────────
    def _direction_to_offset(self, d: str) -> LVector3f:
        return {
            "north": LVector3f(0,  self.CELL, 0),
            "south": LVector3f(0, -self.CELL, 0),
            "east":  LVector3f( self.CELL, 0, 0),
            "west":  LVector3f(-self.CELL, 0, 0),
        }[d]

    def _vec_to_tuple(self, vec: LVector3f) -> tuple[int,int]:
        return (round(vec.getX()), round(vec.getY()))

    @staticmethod
    def _opposite(d: str | None) -> str | None:
        return {"north":"south","south":"north","east":"west","west":"east"}.get(d)

    def _criar_sala_final(self):
        sala_final = NodePath("SalaFinal")
        offset = self._direction_to_offset(self.exit_dir or "north") * 1.5
        sala_final.setPos(self.rooms[-1].getPos() + offset)
        self.sala_final_node = sala_final
        self.room_positions.append(sala_final.getPos())
        self.rooms.append(sala_final)

        # Cria uma esfera ao redor
        sphere = self.app.loader.loadModel("models/misc/sphere")
        sphere.reparentTo(sala_final)
        sphere.setScale(500)
        sphere.setTwoSided(True)
        sphere.setPos(0, 0, 0)

        texture = self.app.loader.loadTexture("assets/textures/final/final.png")
        texture.setWrapU(texture.WMClamp)
        texture.setWrapV(texture.WMClamp)

        ts = TextureStage.getDefault()
        sphere.setTexture(ts, texture)
        sphere.setTexGen(ts, TexGenAttrib.MEyeSphereMap)

        giro = LerpHprInterval(sphere, duration=60, hpr=(360, 0, 0))
        giro.loop()

        # Chão invisível
        cm = CardMaker("final_floor")
        cm.setFrame(-self.WALL_LEN, self.WALL_LEN, -self.WALL_LEN, self.WALL_LEN)
        floor = sala_final.attachNewNode(cm.generate())
        floor.setHpr(0, -90, 0)
        floor.setZ(0)
        floor.setTransparency(True)
        floor.setColor(1, 1, 1, 0.02)

        # Texto 3D na sala
        texto = OnscreenText(
            text="Parabéns!\nVocê chegou à sala final!",
            pos=(0, 0),
            scale=0.1,
            fg=(1, 1, 0.6, 1),
            align=TextNode.ACenter,
            mayChange=False,
            wordwrap=20,
            bg=(0, 0, 0, 0.8)
        )
        texto.reparentTo(sala_final)
        self._tela_final = texto
        self._mensagem_final = OnscreenText(
            text=(
                "Você atravessou corredores, respondeu enigmas,\n"
                "encarou o desconhecido sem hesitar.\n\n"
                "Agora, o fim da jornada revela sua verdadeira natureza.\n"
                "Não há aplausos, nem troféus…\n"
                "Apenas silêncio, reflexo… e você mesmo.\n\n"
                "Resta apenas uma pergunta:\n"
                "o que fará com o que encontrou dentro de si?"
            ),
            pos=(0, 0),
            scale=0.06,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
            wordwrap=42,
            mayChange=False,
            bg=(0, 0, 0, 0.8)
        )

        def remover_mensagem(task):
            if self._mensagem_final:
                self._mensagem_final.destroy()
            return Task.done

        self.app.taskMgr.doMethodLater(20, remover_mensagem, "remover-mensagem-final")

        sala_final.reparentTo(self.app.render)

