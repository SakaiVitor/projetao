# scene_manager.py
from pathlib import Path
import random
from math import sin

from panda3d.core import (
    NodePath, LVector3f, CardMaker, CollisionNode, CollisionBox, Point3, Vec3,
    CollisionPlane, BitMask32, Plane, TextureStage, TexGenAttrib, TransformState,
    LMatrix4f, LVecBase3f, TextNode, Filename
)
from direct.gui.OnscreenText import OnscreenText
from direct.task import Task
from npc.npc_manager import NPCManager


class SceneManager:
    # ─────────────── CONSTANTES DE SALA ────────────────
    CELL      = 20      # distância entre salas (grade)
    WALL_LEN  = 10      # meia-largura da sala
    WALL_ALT  = 5       # altura da parede
    WALL_THK  = 1       # espessura da parede
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

        self.npc_manager   = NPCManager(app)
        self.textures      = [f"assets/textures/floor{i}.jpg" for i in range(1, 7)]
        self.wall_textures = [f"assets/textures/walls/wall{i}.png" for i in range(1, 4)]

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
        for i in range(5):                      # TOTAL = 5
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

    def abrir_porta(self) -> None:
        """Remove completamente a porta da cena, incluindo colisores ocultos."""
        if self.door_node and not self.door_node.isEmpty():
            if self._quiz_passed():
                print(f"[abrir_porta] Abrindo {self.door_node.getName()}")

                print("[abrir_porta] Antes do removeNode():")
                self.door_node.ls()  # Mostra estrutura da porta

                # Remove do grafo de cena completamente
                self.door_node.removeNode()

                print("[abrir_porta] Porta removida com sucesso.")

    # ───────────────────── BUILD DE SALA ─────────────────────
    def _build_room_contents(
        self,
        parent: NodePath,
        entry_dir: str | None,
        force_exit_dir: str | None = None,
        is_first: bool = False
    ) -> None:
        """Gera todo o conteúdo de uma sala."""
        parent.setTag("wall_texture", random.choice(self.wall_textures))

        self._generate_floor(parent)
        self._generate_ceiling(parent)
        self._generate_walls_and_doors(parent, entry_dir, force_exit_dir, is_first)
        self._spawn_npc(parent, entry_dir)
        self._scatter_decor(parent, entry_dir)

    # ──────────── ESTRUTURAS: CHÃO / TETO ─────────────
    def _generate_floor(self, parent: NodePath) -> None:
        cm = CardMaker("floor")
        cm.setFrame(-self.WALL_LEN, self.WALL_LEN,
                    -self.WALL_LEN, self.WALL_LEN)
        floor_vis = parent.attachNewNode(cm.generate())
        floor_vis.setHpr(0, -90, 0)
        floor_vis.setZ(0)
        self._apply_random_texture(floor_vis)

        # colisão = plano infinito em Z=0
        plane   = Plane(Vec3(0, 0, 1), Point3(0, 0, 0))
        cplane  = CollisionPlane(plane)
        cnode   = CollisionNode("floor_collision")
        cnode.addSolid(cplane)
        cnode.setIntoCollideMask(BitMask32.bit(1))
        parent.attachNewNode(cnode).setZ(0)

    def _generate_ceiling(self, parent: NodePath) -> None:
        cm = CardMaker("ceiling")
        cm.setFrame(-self.WALL_LEN, self.WALL_LEN,
                    -self.WALL_LEN, self.WALL_LEN)
        ceiling = parent.attachNewNode(cm.generate())
        ceiling.setPos(0, 0, self.WALL_ALT)
        ceiling.setHpr(0, 90, 0)
        ceiling.setColor(0.8, 0.8, 0.8, 1)

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
            door_dirs = [force_exit_dir]             # 1ª sala → só saída Norte
        else:
            remaining = [d for d in dirs if d != entry_dir]
            door_dirs = [entry_dir, random.choice(remaining)]

        # self.exit_dir = última posição da lista (saída)
        self.exit_dir = door_dirs[-1]
        self.door_node = None

        for d in dirs:
            if d in door_dirs:                       # parede com porta
                self._create_wall_with_door(parent, d)
                door = self._create_door_only(parent, d)
                if d == self.exit_dir:
                    self.door_node = door
            else:                                    # parede sólida
                self._create_wall(parent, d)

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
                       self.WALL_LEN + self.WALL_THK / 2
                       if d == "north" else
                       -self.WALL_LEN - self.WALL_THK / 2,
                       wall_z)
            else:
                piece.setScale(self.WALL_THK, frame_half, self.WALL_ALT + .5)
                y = side * (self.WALL_LEN - frame_half / 2)
                pos = ( self.WALL_LEN + self.WALL_THK / 2
                        if d == "east" else
                       -self.WALL_LEN - self.WALL_THK / 2,
                       y, wall_z)

            piece.setPos(*pos)
            self._apply_room_texture(parent, piece)
            piece.reparentTo(parent)

            # colisor
            sx, sy, sz = piece.getScale()
            box = CollisionBox((0, 0, self.WALL_ALT/2), sx, sy, self.WALL_ALT/2)
            col_np = piece.attachNewNode(CollisionNode(f"wall-col-{d}-{side}"))
            col_np.node().addSolid(box)
            col_np.node().setIntoCollideMask(BitMask32.bit(1))

    def _create_door_only(self, parent: NodePath, d: str) -> NodePath:
        """Modelinho da porta, só para visual (sem colisor)."""
        door = self.app.loader.loadModel("models/misc/rgbCube")
        pos_map = {
            "north": (0,  self.WALL_LEN + self.DOOR_THK/2, self.WALL_ALT/2),
            "south": (0, -self.WALL_LEN - self.DOOR_THK/2, self.WALL_ALT/2),
            "east":  ( self.WALL_LEN + self.DOOR_THK/2, 0, self.WALL_ALT/2),
            "west":  (-self.WALL_LEN - self.DOOR_THK/2, 0, self.WALL_ALT/2),
        }
        if d in ("north", "south"):
            door.setScale(self.DOOR_W, self.DOOR_THK, self.WALL_ALT + .5)
        else:
            door.setScale(self.DOOR_THK, self.DOOR_W, self.WALL_ALT + .5)

        door.setPos(*pos_map[d])
        door.setColor(0.4, 0.2, 0.1, 1)
        door.reparentTo(parent)
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
            box = CollisionBox((0, 0, self.WALL_ALT/2),
                               self.CELL, self.WALL_THK, self.WALL_ALT/2)
        else:
            wall.setScale(self.WALL_THK, self.CELL, self.WALL_ALT)
            box = CollisionBox((0, 0, self.WALL_ALT/2),
                               self.WALL_THK, self.CELL, self.WALL_ALT/2)

        self._apply_room_texture(parent, wall)
        wall.reparentTo(parent)

        col_np = wall.attachNewNode(CollisionNode(f"wall-col-{d}"))
        col_np.node().addSolid(box)
        col_np.node().setIntoCollideMask(BitMask32.bit(1))

    # ───────────── SPAWN DE NPC ─────────────
    def _spawn_npc(self, parent: NodePath, entry_dir: str | None) -> None:
        offsets = {
            "north": ( 2,  self.WALL_LEN - 1, 0),
            "south": ( 2, -self.WALL_LEN + 1, 0),
            "west":  (-self.WALL_LEN + 1, -2, 0),
            "east":  ( self.WALL_LEN - 1, -2, 0),
        }
        if self.exit_dir in offsets:
            npc = self.npc_manager.spawn_npc(
                position=LVector3f(*offsets[self.exit_dir]),
                facing_direction=self._opposite(self.exit_dir),
                door_node=self.door_node  # <-- NOVO
            )
            npc.reparentTo(parent)

    # ──────────── DECORAÇÃO ────────────
    def _scatter_decor(self, parent: NodePath, entry_dir: str | None) -> None:
        blocked = {self.exit_dir}
        if entry_dir:
            blocked.add(entry_dir)
        decor_dirs = [d for d in ("north", "south", "west", "east")
                      if d not in blocked]

        pos_map = {
            "north": (0,  self.WALL_LEN - 1.2, 0),
            "south": (0, -self.WALL_LEN + 1.2, 0),
            "west":  (-self.WALL_LEN + 1.2, 0, 0),
            "east":  ( self.WALL_LEN - 1.2, 0, 0),
        }
        heading_map = {"north": 180, "south": 0, "west": 90, "east": 270}

        obj_dir = Path("assets/models/objects")
        obj_paths = list(obj_dir.glob("*.obj"))
        if not obj_paths:
            print("[SceneManager] Nenhum .obj em assets/models/objects")
            return

        placed: list[LVector3f] = []

        for d in decor_dirs:
            base_x, base_y, base_z = pos_map[d]
            for _ in range(random.randint(1, 3)):
                model_path = random.choice(obj_paths)

                for _attempt in range(10):
                    offset = random.uniform(-2.5, 2.5)
                    pos = (LVector3f(base_x + offset, base_y, base_z + .2)
                           if d in ("north", "south")
                           else LVector3f(base_x, base_y + offset, base_z + .2))

                    if all((pos - p).length() >= 1.5 for p in placed):
                        model = self.app.loader.loadModel(str(model_path))
                        model.setPos(pos)
                        model.setScale(random.uniform(2.2, 3.2))
                        model.setH(heading_map[d] + 90)

                        min_bound, _ = model.getTightBounds()
                        if min_bound:
                            model.setZ(model.getZ() - min_bound.getZ() - .05)

                        model.reparentTo(parent)
                        placed.append(pos)
                        break

    # ────────────── TEXTURAS ──────────────
    def _apply_room_texture(self, room: NodePath, node: NodePath) -> None:
        texture_path = room.getTag("wall_texture")
        texture = self.app.loader.loadTexture(texture_path)

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

    # ────────────── QUIZ / PORTA ──────────────
    def _quiz_passed(self) -> bool:
        return True   # trocar pela lógica real de quiz

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

    def atualizar_sala_baseada_na_posicao(self, player_pos: LVector3f) -> None:
        for i, sala_pos in enumerate(self.room_positions):
            if (abs(player_pos.getX()-sala_pos.getX()) <= self.CELL/2 and
                abs(player_pos.getY()-sala_pos.getY()) <= self.CELL/2):
                if self.room_index != i:
                    self.room_index = i
                    if self._mapa_visivel:
                        self.atualizar_sala_atual_no_mapa()
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
