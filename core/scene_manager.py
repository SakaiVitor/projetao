import random
from panda3d.core import NodePath, LVector3f
from npc.npc_manager import NPCManager

class SceneManager:
    def __init__(self, app):
        self.app = app
        self.current_room = None
        self.room_index = 0
        self.door_node = None
        self.door_position = None

        self.next_room_generated = False

        self.npc_manager = NPCManager(app)

        self.decorative_models = [
            "models/misc/rgbCube"
        ]

        self.textures = [
            f"assets/textures/grass_{i:02}.jpg" for i in range(1, 11)
        ]

    def load_first_room(self):
        self.load_room()
        self.next_room_generated = False

    def load_room(self):
        if self.current_room:
            self.current_room.removeNode()

        self.current_room = NodePath(f"Room-{self.room_index}")
        self.current_room.reparentTo(self.app.render)

        self._generate_floor()
        self._generate_walls()
        self._generate_door()
        self._spawn_npc()
        self._scatter_random_objects(random.randint(3, 6))

        self.room_index += 1

    def _apply_random_texture_or_color(self, node):
        if random.random() < 0.5 and self.textures:
            texture = self.app.loader.loadTexture(random.choice(self.textures))
            node.setTexture(texture, 1)
        else:
            node.setColor(random.random(), random.random(), random.random(), 1)

    def _generate_floor(self):
        floor = self.app.loader.loadModel("models/environment")
        floor.setScale(10, 10, 1)
        floor.setPos(0, 0, 0)
        self._apply_random_texture_or_color(floor)
        floor.reparentTo(self.current_room)

    def _generate_walls(self):
        positions = [
            (0, -10, 1),  # sul
            (0, 10, 1),   # norte
            (-10, 0, 1),  # oeste
            (10, 0, 1)    # leste
        ]
        hpr_values = [(0, 0, 0), (0, 0, 0), (90, 0, 0), (90, 0, 0)]

        for i, pos in enumerate(positions):
            wall = self.app.loader.loadModel("models/misc/rgbCube")
            wall.setScale(1, 10, 2)
            wall.setPos(*pos)
            wall.setHpr(*hpr_values[i])
            self._apply_random_texture_or_color(wall)
            wall.reparentTo(self.current_room)

    def _generate_door(self):
        from panda3d.core import LVector3f

        possible_positions = {
            "north": LVector3f(0, 10.1, 1),
            "west": LVector3f(-10.1, 0, 1),
            "east": LVector3f(10.1, 0, 1)
        }

        direction = random.choice(list(possible_positions.keys()))
        pos = possible_positions[direction]

        self.door_node = self.app.loader.loadModel("models/misc/rgbCube")
        self.door_node.setScale(1, 2, 2)
        self.door_node.setPos(pos)

        if direction in ["west", "east"]:
            self.door_node.setH(90)

        # Porta sempre marrom
        self.door_node.setColor(0.55, 0.27, 0.07, 1)

        # Se for porta "aberta" (modo de teste), esconda visualmente
        if getattr(self, 'force_doors_open', False):
            self.door_node.hide()

        self.door_node.reparentTo(self.current_room)
        self.door_position = direction

    def abrir_porta(self):
        """Abre visualmente a porta atual (faz ela sumir)"""
        if self.door_node and not self.door_node.isEmpty():
            self.door_node.hide()

    def _spawn_npc(self):
        npc = self.npc_manager.spawn_npc(position=LVector3f(0, 0, 0))
        npc.reparentTo(self.current_room)

    def _scatter_random_objects(self, count=5):
        for _ in range(count):
            model_path = random.choice(self.decorative_models)
            try:
                model = self.app.loader.loadModel(model_path)
                x = random.uniform(-8, 8)
                y = random.uniform(-8, 8)
                z = 0
                model.setPos(x, y, z)
                model.setH(random.uniform(0, 360))
                model.setScale(random.uniform(0.5, 1.5))
                model.reparentTo(self.current_room)
            except Exception as e:
                print(f"Erro ao carregar modelo {model_path}: {e}")
