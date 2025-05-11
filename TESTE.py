from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    CollisionTraverser, CollisionHandlerPusher,
    CollisionNode, CollisionSphere, CollisionBox, CollisionPlane,
    BitMask32, Vec3, WindowProperties,
    CardMaker, Plane, Point3, ClockObject
)

globalClock = ClockObject.getGlobalClock()

class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # ───── Colisão ─────
        self.cTrav = CollisionTraverser()
        self.pusher = CollisionHandlerPusher()

        # ───── Jogador ─────
        self.player = self.render.attachNewNode("Player")
        self.player.setPos(0, 0, 1)

        cnode = CollisionNode("playerCollider")
        cnode.addSolid(CollisionSphere(0, 0, 0, 1))
        cnode.setFromCollideMask(BitMask32.bit(1))
        cnode.setIntoCollideMask(BitMask32.allOff())
        collider = self.player.attachNewNode(cnode)

        self.pusher.addCollider(collider, self.player)
        self.cTrav.addCollider(collider, self.pusher)

        self.cTrav.showCollisions(self.render)

        # ───── Parede ─────
        wall = self.loader.loadModel("models/misc/rgbCube")
        wall.setScale(10, 1, 5)
        wall.setPos(0, 10, 2.5)
        wall.reparentTo(self.render)

        wall_cnode = CollisionNode("wallCollider")
        wall_cnode.addSolid(CollisionBox((0, 0, 0), 10, 1.1, 2.5))
        wall_cnode.setIntoCollideMask(BitMask32.bit(1))
        wall.attachNewNode(wall_cnode)

        # ───── CHÃO VISUAL ─────
        cm = CardMaker("ground")
        cm.setFrame(-50, 50, -50, 50)
        floor = self.render.attachNewNode(cm.generate())
        floor.setHpr(0, -90, 0)
        floor.setPos(0, 0, 0)
        floor.setColor(0.3, 0.3, 0.3, 1)
        floor.setColor(0.5, 0.5, 0.5, 1)

        # ───── CHÃO COLISÃO ─────
        plane = Plane(Vec3(0, 0, 1), Point3(0, 0, 0))  # plano Z=0
        cnode_floor = CollisionNode("floorCollider")
        cnode_floor.addSolid(CollisionPlane(plane))
        cnode_floor.setIntoCollideMask(BitMask32.bit(1))
        floor.attachNewNode(cnode_floor)

        plane2 = Plane(Vec3(0, 1, 0), Point3(0, 0, 0))  # plano Z=0
        cnode_floor2 = CollisionNode("floorCollider2")
        cnode_floor2.addSolid(CollisionPlane(plane2))
        cnode_floor2.setIntoCollideMask(BitMask32.bit(1))
        floor.attachNewNode(cnode_floor2)

        # ───── Câmera ─────
        self.disableMouse()
        self.camera.reparentTo(self.player)
        self.camera.setPos(0, 0, 1.5)

        # ───── Mouse Lock ─────
        props = WindowProperties()
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_relative)
        self.win.requestProperties(props)

        # ───── Input ─────
        self.keys = {"w": False, "s": False, "a": False, "d": False}
        for key in self.keys:
            self.accept(key, self.set_key, [key, True])
            self.accept(f"{key}-up", self.set_key, [key, False])

        self.accept("escape", exit)

        self.heading = 0
        self.pitch = 0
        self.sensitivity = 0.2

        self.taskMgr.add(self.update, "update")

    def set_key(self, key, value):
        self.keys[key] = value

    def update(self, task):
        dt = globalClock.getDt()
        speed = 5

        # Mouse look
        mpos = self.win.getPointer(0)
        win_cx = self.win.getXSize() // 2
        win_cy = self.win.getYSize() // 2
        dx = mpos.getX() - win_cx
        dy = mpos.getY() - win_cy

        self.heading -= dx * self.sensitivity
        self.pitch -= dy * self.sensitivity
        self.pitch = max(-90, min(90, self.pitch))

        self.player.setH(self.heading)
        self.camera.setP(self.pitch)
        self.win.movePointer(0, win_cx, win_cy)

        # Movimento
        direction = Vec3(0, 0, 0)
        if self.keys["w"]: direction += Vec3(0, 1, 0)
        if self.keys["s"]: direction += Vec3(0, -1, 0)
        if self.keys["a"]: direction += Vec3(-1, 0, 0)
        if self.keys["d"]: direction += Vec3(1, 0, 0)

        if direction.length() > 0:
            direction.normalize()
            move_vec = self.player.getQuat().xform(direction) * speed * dt
            self.player.setFluidPos(self.player.getPos() + move_vec)

        self.cTrav.traverse(self.render)
        print(f"[controller.py - update] Posição do jogador: {self.player.getPos()}")

        return task.cont

game = Game()
game.run()
