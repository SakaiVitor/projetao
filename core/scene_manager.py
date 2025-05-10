from panda3d.core import (
    NodePath, LVector3f, CardMaker, CollisionNode, CollisionBox, BitMask32
)
import random
from npc.npc_manager import NPCManager

class SceneManager:
    CELL      = 20              # distância entre salas
    WALL_LEN  = 10              # meia‐largura da sala
    WALL_ALT  = 2               # altura da parede
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

        self.npc_manager = NPCManager(app)
        self.decorative_models = ["models/misc/rgbCube"]
        self.textures = [f"assets/textures/grass_{i:02}.jpg" for i in range(1, 11)]
        self.room_positions = [LVector3f(0, 0, 0)]

    # ───────────────────────────  PÚBLICOS  ────────────────────────────
    def load_first_room(self):
        self.current_room = NodePath("Room-0")
        self.current_room.setPos(self.room_positions[0])
        self._build_room_contents(self.current_room, entry_dir=None, is_first=True)
        self.current_room.reparentTo(self.app.render)

        self.room_index = 1
        self._preload_next_room()

    def load_room(self):
        # NÃO removemos mais a sala anterior do render!
        # if self.current_room:
        #     self.current_room.detachNode()

        # Ativa a próxima sala
        self.current_room = self.next_room
        self.current_room.reparentTo(self.app.render)

        self.room_index += 1
        self._preload_next_room()

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
        self._generate_floor(parent)
        print(f"[scene_manager.py - _build_room_contents] Chão gerado na posição: {parent.getPos()}")

        self._generate_ceiling(parent)
        print(f"[scene_manager.py - _build_room_contents] Teto gerado na posição: {parent.getPos()}")

        self._generate_walls_and_doors(parent, entry_dir, is_first)
        self._spawn_npc(parent)
        self._scatter_decor(parent)

    def _generate_floor(self, parent):
        cm = CardMaker("floor")
        cm.setFrame(-self.WALL_LEN, self.WALL_LEN, -self.WALL_LEN, self.WALL_LEN)
        floor = parent.attachNewNode(cm.generate())
        floor.setHpr(0, -90, 0)
        floor.setZ(0)
        floor.setCollideMask(BitMask32.allOff())  # Garanta que o chão não tenha colisão!
        self._apply_random_texture_or_color(floor)

    def _generate_ceiling(self, parent):
        cm = CardMaker("ceiling"); cm.setFrame(-self.WALL_LEN, self.WALL_LEN, -self.WALL_LEN, self.WALL_LEN)
        ceiling = parent.attachNewNode(cm.generate())
        ceiling.setPos(0, 0, self.WALL_ALT + .5)
        ceiling.setHpr(0,  90, 0)
        ceiling.setColor(0.8, 0.8, 0.8, 1)

    def _generate_walls_and_doors(self, parent, entry_dir, is_first):
        dirs = ["north", "south", "east", "west"]
        wall_pos = {
            "north": ( 0,  self.WALL_LEN, 1),
            "south": ( 0, -self.WALL_LEN, 1),
            "west":  (-self.WALL_LEN, 0, 1),
            "east":  ( self.WALL_LEN, 0, 1),
        }

        # define portas
        if is_first:
            door_dirs = [random.choice(dirs)]              # apenas 1 porta
        else:
            remaining = [d for d in dirs if d != entry_dir]
            door_dirs = [entry_dir, random.choice(remaining)]

        self.exit_dir = door_dirs[-1]                      # porta de saída da sala atual
        self.door_node = None

        for d in dirs:
            if d in door_dirs:
                door = self._create_door(parent, d, wall_pos[d])
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
            wall.setScale(self.WALL_LEN, self.WALL_THK, self.WALL_ALT)
            collider_box = CollisionBox((0, 0, self.WALL_ALT / 2), self.WALL_LEN, self.WALL_THK, self.WALL_ALT / 2)
        else:  # leste / oeste
            wall.setScale(self.WALL_THK, self.WALL_LEN, self.WALL_ALT)
            collider_box = CollisionBox((0, 0, self.WALL_ALT / 2), self.WALL_THK, self.WALL_LEN, self.WALL_ALT / 2)

        wall.setPos(*pos)
        self._apply_random_texture_or_color(wall)
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
        safe_margin = 2
        num_objects = random.randint(3, 6)

        for _ in range(num_objects):
            model = self.app.loader.loadModel(random.choice(self.decorative_models))
            x = random.uniform(-self.WALL_LEN + safe_margin, self.WALL_LEN - safe_margin)
            y = random.uniform(-self.WALL_LEN + safe_margin, self.WALL_LEN - safe_margin)
            model.setPos(x, y, 0)
            model.setScale(random.uniform(0.25, 0.5))
            model.reparentTo(parent)


    # ───────── misc ─────────
    def _apply_random_texture_or_color(self, node):
        if random.random() < .5:
            node.setColor(random.random(), random.random(), random.random(), 1)
        else:
            node.setTexture(self.app.loader.loadTexture(random.choice(self.textures)), 1)

    def _quiz_passed(self):
        return True

    @staticmethod
    def _opposite(d):
        return {"north":"south","south":"north","east":"west","west":"east"}.get(d)
