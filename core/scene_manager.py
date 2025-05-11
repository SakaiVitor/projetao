from pathlib import Path

from panda3d.core import (
    NodePath, LVector3f, CardMaker, CollisionNode, CollisionBox, Point3, Vec3, CollisionPlane, BitMask32, Plane
)
import random
from npc.npc_manager import NPCManager

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode
from panda3d.core import TextureStage, TexGenAttrib, TransformState, LMatrix4f, LVecBase3f

class SceneManager:
    CELL      = 20              # distância entre salas
    WALL_LEN  = 10              # meia‐largura da sala
    WALL_ALT  = 5               # altura da parede
    WALL_THK  = 1               # espessura da parede
    DOOR_W    = 2               # largura visível da porta
    DOOR_THK  = .4              # profundidade da porta (porta fina)

    def __init__(self, app):
        self.app = app
        self.room_index  = 0
        self.current_room: NodePath | None = None
        self.next_room   : NodePath | None = None
        self.door_node   : NodePath | None = None   # porta de saída da sala ATUAL
        self.exit_dir    = None                    # 'north' | 'south' | 'east' | 'west'
        self.rooms: list[NodePath] = []
        self._mapa_visivel = False
        self._mapa_textos = []
        self.room_grid_set = set()  # ← usado para checar colisão de posição


        self.npc_manager = NPCManager(app)
        self.textures = [f"assets/textures/floor{i:01}.jpg" for i in range(1, 7)]
        self.room_positions = [LVector3f(0, 0, 0)]
        self.wall_textures = [f"assets/textures/walls/wall{i}.png" for i in range(1, 4)]


    # ───────────────────────────  PÚBLICOS  ────────────────────────────
    def load_first_room(self):
        current_dir = random.choice(["north", "south", "east", "west"])
        current_pos = LVector3f(0, 0, 0)
        self.room_grid_set = {self._vec_to_tuple(current_pos)}  # adiciona a primeira sala

        for i in range(20):
            room = NodePath(f"Room-{i}")
            room.setPos(current_pos)

            if i == 0:
                self._build_room_contents(room, entry_dir=None, is_first=True)
            else:
                entry_dir = self._opposite(prev_exit_dir)
                self._build_room_contents(room, entry_dir=entry_dir, is_first=False)

            self.rooms.append(room)
            self.room_positions.append(current_pos)

            prev_exit_dir = self.exit_dir  # definido internamente
            next_pos = current_pos + self._direction_to_offset(prev_exit_dir)

            # Tenta encontrar uma posição livre
            tried_dirs = {prev_exit_dir}
            while self._vec_to_tuple(next_pos) in self.room_grid_set:
                # já ocupado → tenta outra direção
                available_dirs = [d for d in ["north", "south", "east", "west"] if d not in tried_dirs]
                if not available_dirs:
                    print(f"[SceneManager] Não há mais direções livres após {i} salas.")
                    break  # encerra mais cedo se não houver mais opções

                prev_exit_dir = random.choice(available_dirs)
                tried_dirs.add(prev_exit_dir)
                next_pos = current_pos + self._direction_to_offset(prev_exit_dir)

            # Atualiza para próxima iteração
            current_pos = next_pos
            self.room_grid_set.add(self._vec_to_tuple(current_pos))

        for room in self.rooms:
            room.reparentTo(self.app.render)

        self.current_room = self.rooms[0]


    def load_next_room(self):
        if self.room_index + 1 < len(self.rooms):
            self.load_room(self.room_index + 1)
        else:
            print("[SceneManager] Fim das salas.")




    def _direction_to_offset(self, direction):
        return {
            "north": LVector3f(0,  self.CELL, 0),
            "south": LVector3f(0, -self.CELL, 0),
            "east":  LVector3f( self.CELL, 0, 0),
            "west":  LVector3f(-self.CELL, 0, 0),
        }.get(direction, LVector3f(0, self.CELL, 0))  # fallback em caso de erro


    def load_room(self, index):
        if 0 <= index < len(self.rooms):
            if self.current_room:
                self.current_room.detachNode()
            self.current_room = self.rooms[index]
            self.current_room.reparentTo(self.app.render)
            self.room_index = index

            if self._mapa_visivel and self._mapa_textos:
                self.atualizar_sala_atual_no_mapa()
            else:
                print("[SceneManager] Mapa não está visível ou ainda não foi gerado.")






    def abrir_porta(self):
        if self.door_node and not self.door_node.isEmpty():
            if self._quiz_passed():
                self.door_node.hide()        # sem colisor → passagem livre

    # ───────────────────────────  INTERNOS  ────────────────────────────
    def _preload_next_room(self):
        # posição depende da porta de saída da sala atual
        pos = self._calculate_next_room_position(self.exit_dir)
        room = NodePath(f"Room-{self.room_index}")
        room.setPos(pos)

        # entrada da próxima sala é o oposto da porta de saída desta sala
        entry_dir = self._opposite(self.exit_dir) if self.exit_dir else None
        self._build_room_contents(room, entry_dir=entry_dir, is_first=False)

        self.next_room = room
        self.room_positions.append(pos)

    def _calculate_next_room_position(self, exit_dir):
        offset = {
            "north": LVector3f(0,  self.CELL, 0),
            "south": LVector3f(0, -self.CELL, 0),
            "east":  LVector3f( self.CELL, 0, 0),
            "west":  LVector3f(-self.CELL, 0, 0),
        }
        return self.room_positions[-1] + offset.get(exit_dir, LVector3f(0, self.CELL, 0))

    # ──────────────────────  CONSTRUÇÃO DA SALA  ───────────────────────
    def _build_room_contents(self, parent, entry_dir, is_first):
        parent.setTag("wall_texture", random.choice(self.wall_textures))
        self._generate_floor(parent)
        print(f"[scene_manager.py - _build_room_contents] Chão gerado na posição: {parent.getPos()}")

        self._generate_ceiling(parent)
        print(f"[scene_manager.py - _build_room_contents] Teto gerado na posição: {parent.getPos()}")

        self._generate_walls_and_doors(parent, entry_dir, is_first)
        self._spawn_npc(parent)
        self._scatter_decor(parent)

    def _generate_floor(self, parent):
        # Parte visual
        cm = CardMaker("floor")
        cm.setFrame(-self.WALL_LEN, self.WALL_LEN, -self.WALL_LEN, self.WALL_LEN)
        floor_vis = parent.attachNewNode(cm.generate())
        floor_vis.setHpr(0, -90, 0)
        floor_vis.setZ(0)
        self._apply_random_texture(floor_vis)

        # Parte de colisão
        plane = Plane(Vec3(0, 0, 1), Point3(0, 0, 0))  # plano horizontal em Z=0
        cplane = CollisionPlane(plane)
        cnode = CollisionNode("floor_collision")
        cnode.addSolid(cplane)
        cnode.setIntoCollideMask(BitMask32.bit(1))  # precisa bater com o ray

        cnode_path = parent.attachNewNode(cnode)
        cnode_path.setZ(0)  # certifique-se de alinhar com o visual

    def _generate_ceiling(self, parent):
        cm = CardMaker("ceiling"); cm.setFrame(-self.WALL_LEN, self.WALL_LEN, -self.WALL_LEN, self.WALL_LEN)
        ceiling = parent.attachNewNode(cm.generate())
        ceiling.setPos(0, 0, self.WALL_ALT)
        ceiling.setHpr(0,  90, 0)
        ceiling.setColor(0.8, 0.8, 0.8, 1)

    def _create_wall_with_door(self, parent, d):
        """Cria uma parede com um 'buraco' (porta) no meio usando dois blocos."""
        is_horizontal = d in ("north", "south")
        wall_z = self.WALL_ALT / 2
        wall_length = self.WALL_LEN
        door_half = self.DOOR_W / 2
        frame_half = (wall_length - door_half)   # Cada batente ocupa essa metade

        for side in (-1, 1):
            piece = self.app.loader.loadModel("models/misc/rgbCube")
            if is_horizontal:
                piece.setScale(frame_half, self.WALL_THK, self.WALL_ALT + 0.5)
                x = side * (wall_length - frame_half / 2)
                pos = (x, self.WALL_LEN + self.WALL_THK / 2, wall_z) if d == "north" else (x, -self.WALL_LEN - self.WALL_THK / 2, wall_z)
            else:
                piece.setScale(self.WALL_THK, frame_half, self.WALL_ALT + 0.5)
                y = side * (wall_length - frame_half / 2)
                pos = (self.WALL_LEN + self.WALL_THK / 2, y, wall_z) if d == "east" else (-self.WALL_LEN - self.WALL_THK / 2, y, wall_z)

            piece.setPos(*pos)
            # self._apply_random_texture(piece)
            self._apply_room_texture(parent, piece)
            piece.reparentTo(parent)

            scale = piece.getScale()
            collider_box = CollisionBox((0, 0, self.WALL_ALT / 2), scale.getX(), scale.getY(), self.WALL_ALT / 2)

            col_np = piece.attachNewNode(CollisionNode(f"wall-col-{d}-{side}"))
            col_np.node().addSolid(collider_box)
            col_np.node().setIntoCollideMask(BitMask32.bit(1))

    def _create_door_only(self, parent, d):
        """Porta decorativa colocada no centro do buraco da parede"""
        door = self.app.loader.loadModel("models/misc/rgbCube")
        pos_map = {
            "north": (0,  self.WALL_LEN + self.DOOR_THK / 2, self.WALL_ALT / 2),
            "south": (0, -self.WALL_LEN - self.DOOR_THK / 2, self.WALL_ALT / 2),
            "east":  (self.WALL_LEN + self.DOOR_THK / 2, 0, self.WALL_ALT / 2),
            "west":  (-self.WALL_LEN - self.DOOR_THK / 2, 0, self.WALL_ALT / 2),
        }

        if d in ("north", "south"):
            door.setScale(self.DOOR_W, self.DOOR_THK, self.WALL_ALT + 0.5)
        else:
            door.setScale(self.DOOR_THK, self.DOOR_W, self.WALL_ALT + 0.5)

        door.setPos(*pos_map[d])
        door.setColor(0.4, 0.2, 0.1, 1)
        door.reparentTo(parent)
        return door


    def _generate_walls_and_doors(self, parent, entry_dir, is_first):
        dirs = ["north", "south", "east", "west"]
        wall_pos = {
            "north": ( 0,  self.WALL_LEN, 1),
            "south": ( 0, -self.WALL_LEN, 1),
            "west":  (-self.WALL_LEN, 0, 1),
            "east":  ( self.WALL_LEN, 0, 1),
        }

        if is_first:
            door_dirs = [random.choice(dirs)]  # Apenas uma saída
        else:
            remaining = [d for d in dirs if d != entry_dir]
            door_dirs = [entry_dir, random.choice(remaining)]

        self.exit_dir = door_dirs[-1]
        self.door_node = None

        for d in dirs:
            if d in door_dirs:
                self._create_wall_with_door(parent, d)
                door = self._create_door_only(parent, d)
                if d == self.exit_dir:
                    self.door_node = door
            else:
                self._create_wall(parent, d, wall_pos[d])


    # ───── helpers de construção ─────
    def _create_wall(self, parent, d, pos):
        wall = self.app.loader.loadModel("models/misc/rgbCube")

        # Posição ajustada para encostar na borda da sala com espessura considerada
        positions = {
            "north": (0,  self.WALL_LEN + self.WALL_THK / 2, self.WALL_ALT / 2),
            "south": (0, -self.WALL_LEN - self.WALL_THK / 2, self.WALL_ALT / 2),
            "east":  (self.WALL_LEN + self.WALL_THK / 2, 0, self.WALL_ALT / 2),
            "west":  (-self.WALL_LEN - self.WALL_THK / 2, 0, self.WALL_ALT / 2),
        }
        pos = positions[d]

        # Escala e orientação
        if d in ("north", "south"):
            wall.setScale(self.CELL, self.WALL_THK, self.WALL_ALT)
            collider_box = CollisionBox((0, 0, self.WALL_ALT / 2), self.CELL, self.WALL_THK, self.WALL_ALT / 2)
        else:  # leste / oeste
            wall.setScale(self.WALL_THK, self.CELL, self.WALL_ALT)
            collider_box = CollisionBox((0, 0, self.WALL_ALT / 2), self.WALL_THK, self.CELL, self.WALL_ALT / 2)

        wall.setPos(*pos)
        # self._apply_random_texture(wall)
        self._apply_room_texture(parent, wall)
        wall.reparentTo(parent)

        col_np = wall.attachNewNode(CollisionNode(f"wall-col-{d}"))
        col_np.node().addSolid(collider_box)
        col_np.node().setIntoCollideMask(BitMask32.bit(1))


    def _create_door(self, parent, d, pos):
        door = self.app.loader.loadModel("models/misc/rgbCube")

        # Posição ajustada como nas paredes
        positions = {
            "north": (0,  self.WALL_LEN + self.DOOR_THK / 2, self.WALL_ALT / 2),
            "south": (0, -self.WALL_LEN - self.DOOR_THK / 2, self.WALL_ALT / 2),
            "east":  (self.WALL_LEN + self.DOOR_THK / 2, 0, self.WALL_ALT / 2),
            "west":  (-self.WALL_LEN - self.DOOR_THK / 2, 0, self.WALL_ALT / 2),
        }
        pos = positions[d]

        if d in ("north", "south"):
            door.setScale(self.WALL_LEN / 3, self.DOOR_THK, self.WALL_ALT)
        else:
            door.setScale(self.DOOR_THK, self.WALL_LEN / 3, self.WALL_ALT)

        door.setPos(*pos)
        door.setColor(0.55, 0.27, 0.07, 1)
        door.reparentTo(parent)
        return door   # sem colisor para poder ser “aberta”
    
    def _apply_room_texture(self, room: NodePath, node: NodePath):
        texture_path = room.getTag("wall_texture")
        print(f"[DEBUG] Aplicando textura: {texture_path} na sala {room.getName()}")
        texture = self.app.loader.loadTexture(texture_path)

        node.setColor(1, 1, 1, 1)

        ts = TextureStage.getDefault()
        node.setTexture(ts, texture)
        node.setTexGen(ts, TexGenAttrib.MWorldPosition)

        # Rotação + escala
        scale_x = 0.2
        scale_y = 0.4
        rotation_degrees = 90

        rotation = LMatrix4f.rotateMat(rotation_degrees, LVecBase3f(0, 0, 1))
        scale = LMatrix4f.scaleMat(scale_x, scale_y, 1)
        matrix = rotation
        matrix *= scale  # ← aplica a rotação antes da escala

        tex_transform = TransformState.makeMat(matrix)
        node.setTexTransform(ts, tex_transform)


    def _spawn_npc(self, parent):
        offsets = {
            "north": ( 2,  self.WALL_LEN-1, 0),
            "south": ( 2, -self.WALL_LEN+1, 0),
            "west":  (-self.WALL_LEN+1, -2, 0),
            "east":  ( self.WALL_LEN-1, -2, 0),
        }
        if self.exit_dir in offsets:
            npc = self.npc_manager.spawn_npc(position=LVector3f(*offsets[self.exit_dir]))
            npc.reparentTo(parent)

    def _scatter_decor(self, parent):
        decor_dirs = [d for d in ("north", "south", "west", "east") if d != self.exit_dir]
        pos_map = {
            "north": (0, self.WALL_LEN - 3, 0),
            "south": (0, -self.WALL_LEN + 3, 0),
            "west": (-self.WALL_LEN + 3, 0, 0),
            "east": (self.WALL_LEN - 3, 0, 0),
        }

        # Busca dinâmica dos .obj
        obj_dir = Path("assets/models/objects")
        obj_paths = list(obj_dir.glob("*.obj"))
        if not obj_paths:
            print("[SceneManager] Nenhum arquivo .obj encontrado em assets/models/objects")
            return

        placed_positions = []

        for d in decor_dirs:
            px, py, pz = pos_map[d]
            for _ in range(random.randint(1, 3)):
                model_path = random.choice(obj_paths)
                for _attempt in range(10):
                    dx, dy = random.uniform(-3, 3), random.uniform(-3, 3)
                    pos = LVector3f(px + dx, py + dy, pz + 0.3)

                    if all((pos - other).length() >= 1.5 for other in placed_positions):
                        model = self.app.loader.loadModel(str(model_path))
                        model.setPos(pos)
                        model.setScale(random.uniform(1, 1.5))
                        model.setHpr(random.uniform(0, 360), 0, 0)  # apenas rotação em Z

                        min_bound, _ = model.getTightBounds()
                        if min_bound:
                            model.setZ(model.getZ() - min_bound.getZ() - 0.05)

                        model.reparentTo(parent)
                        placed_positions.append(pos)
                        break


    # ───────── misc ─────────
    def _apply_random_texture(self, node):
        texture_path = random.choice(self.textures)
        texture = self.app.loader.loadTexture(texture_path)
        node.setTexture(texture, 1)

    def _quiz_passed(self):
        return True
    
    def _vec_to_tuple(self, vec: LVector3f):
        return (round(vec.getX()), round(vec.getY()))
    
    #-------------------MAPAS VISÍVEIS-------------------
    def gerar_mapa_resumo(self):
        center_x = 0.7
        center_y = 0.7
        scale = 0.05
        offset = 0.06

        min_x = min(p.getX() for p in self.room_positions)
        min_y = min(p.getY() for p in self.room_positions)

        self._mapa_textos = []

        for i, pos in enumerate(self.room_positions):
            grid_x = int((pos.getX() - min_x) / self.CELL)
            grid_y = int((pos.getY() - min_y) / self.CELL)

            text = OnscreenText(
                text=str(i),
                pos=(center_x - offset * grid_x, center_y - offset * grid_y),
                scale=scale,
                fg=(1, 1, 1, 1),
                bg=(1, 0, 0, 0.7) if i == self.room_index else (0, 0, 0, 0.6),
                align=TextNode.ACenter,
                mayChange=True
            )
            self._mapa_textos.append(text)

        self._mapa_visivel = True


    def esconder_mapa_resumo(self):
        for t in self._mapa_textos:
            t.destroy()
        self._mapa_textos = []
        self._mapa_visivel = False


    def toggle_mapa_resumo(self):
        if self._mapa_visivel:
            self.esconder_mapa_resumo()
        else:
            self.gerar_mapa_resumo()

    def atualizar_sala_atual_no_mapa(self):
        print(f"[Mapa] Atualizando destaque para sala {self.room_index}")
        if not self._mapa_textos:
            print("[SceneManager] Nenhum texto de mapa disponível.")
            return

        for i, t in enumerate(self._mapa_textos):
            if t is None:
                continue
            if i == self.room_index:
                t.setBg((1, 0, 0, 0.7))  # vermelho
            else:
                t.setBg((0, 0, 0, 0.6))  # fundo padrão

    def atualizar_sala_baseada_na_posicao(self, player_pos: LVector3f):
        """
        Atualiza o índice da sala atual com base na posição do jogador.
        """
        for i, sala_pos in enumerate(self.room_positions):
            # Verifica se jogador está dentro do volume da sala
            dx = abs(player_pos.getX() - sala_pos.getX())
            dy = abs(player_pos.getY() - sala_pos.getY())
            if dx <= self.CELL / 2 and dy <= self.CELL / 2:
                if self.room_index != i:
                    print(f"[SceneManager] Jogador entrou na sala {i}")
                    self.room_index = i
                    if self._mapa_visivel:
                        self.atualizar_sala_atual_no_mapa()
                return



    @staticmethod
    def _opposite(d):
        return {"north":"south","south":"north","east":"west","west":"east"}.get(d)
