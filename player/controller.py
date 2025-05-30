from direct.showbase.ShowBaseGlobal import globalClock
from panda3d.core import Vec3, WindowProperties
from panda3d.core import CollisionTraverser, CollisionHandlerPusher, CollisionNode, CollisionSphere, BitMask32, CollisionCapsule
from direct.showbase.Audio3DManager import Audio3DManager
import random, time

class PlayerController:
    def __init__(self, app):
        self.app = app
        self.moving = True
        self.speed = 10
        self.mouse_sensitivity = 0.2
        self.pitch = 0.0

        # ── Dummy Node que representa o jogador de verdade ─────
        self.node = self.app.render.attachNewNode("PlayerNode")
        self.node.setPos(0, 0, 2)

        # ── Modelo visual do jogador ───────────────────────────
        self.actor = self.app.loader.loadModel("models/misc/rgbCube")
        self.actor.setScale(1.0)
        self.actor.setZ(0)  # para que a base fique em z=0
        self.actor.setColor(0, 1, 1, 1)
        self.actor.reparentTo(self.node)

        # ── Câmera presa ao dummy node ─────────────────────────
        self.app.disableMouse()
        self.app.camera.reparentTo(self.node)
        self.app.camera.setZ(0.75)  # altura dos "olhos"

        # ── Controles de teclado ───────────────────────────────
        self.keys = {"w": False, "s": False, "a": False, "d": False}
        self.setup_controls()

        # ── Sistema de colisão ─────────────────────────────────
        # self.cTrav = CollisionTraverser()
        self.cTrav = self.app.cTrav
        print("[DEBUG] Tipo de self.cTrav:", type(self.cTrav))

        self.pusher = CollisionHandlerPusher()

        cnode = CollisionNode("playerCollider")
        cnode.addSolid(CollisionCapsule(0, 0, 0, 0, 0, 5, 0.8))
        self.app.camera.setPos(0, -0.15, 0.75)

        cnode.setFromCollideMask(BitMask32.bit(1))
        cnode.setIntoCollideMask(BitMask32.allOff())

        self.collider_node = self.node.attachNewNode(cnode)
        self.pusher.addCollider(self.collider_node, self.node)
        self.cTrav.addCollider(self.collider_node, self.pusher)

        # ── Travar mouse no centro ─────────────────────────────
        self.app.taskMgr.doMethodLater(0.1, lambda task: self.lock_mouse() or task.done, "lockMouse")

        # ── Loop de atualização ───────────────────────────────
        self.app.taskMgr.add(self.update, "PlayerControllerUpdate")

        self.audio3d = Audio3DManager(self.app.sfxManagerList[0], self.app.camera)
        self.ultimo_passo = 0.0
        self.intervalo_passo = 0.65  # bem espaçados

    def setup_controls(self):
        for key in self.keys:
            self.app.accept(key, self.set_key, [key, True])
            self.app.accept(f"{key}-up", self.set_key, [key, False])
        self.app.accept("tab", self.toggle_prompt)

    def set_key(self, key, value):
        self.keys[key] = value

    def toggle_prompt(self):
        if self.app.hud.entry:
            self.app.hud.close_prompt()
            self.moving = True
        else:
            self.app.hud.show_prompt()
            self.moving = False

    def lock_mouse(self):
        props = WindowProperties()
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_relative)
        self.app.win.requestProperties(props)

    def update(self, task):
        dt = globalClock.getDt()
        if not self.moving or not self.app.mouseWatcherNode.hasMouse():
            return task.cont

        # ── MOUSE LOOK ──────────────────────────────
        mpos = self.app.win.getPointer(0)
        win_cx = self.app.win.getXSize() // 2
        win_cy = self.app.win.getYSize() // 2
        dx = mpos.getX() - win_cx
        dy = mpos.getY() - win_cy

        self.node.setH(self.node.getH() - dx * self.mouse_sensitivity)
        self.pitch -= dy * self.mouse_sensitivity
        self.pitch = max(-89, min(89, self.pitch))
        self.app.camera.setP(self.pitch)
        self.app.win.movePointer(0, win_cx, win_cy)

        # ── MOVIMENTO ───────────────────────────────
        direction = Vec3(0, 0, 0)
        if self.keys["w"]: direction += Vec3(0, 1, 0)
        if self.keys["s"]: direction += Vec3(0, -1, 0)
        if self.keys["a"]: direction += Vec3(-1, 0, 0)
        if self.keys["d"]: direction += Vec3(1, 0, 0)

        if direction.length() > 0:
            direction.normalize()
            world_dir = self.node.getQuat().xform(direction)
            # self.node.setPos(self.node.getPos() + world_dir * self.speed * dt)
            self.node.setFluidPos(self.node.getPos() + world_dir * self.speed * dt)
            agora = time.time()
            if agora - self.ultimo_passo > self.intervalo_passo:
                som = self.app.loader.loadSfx("assets/sounds/passo.wav")
                som.setVolume(1.0)
                som.play()
                self.ultimo_passo = agora

        self.node.setZ(2)

        # ── COLISÃO ─────────────────────────────────
        self.cTrav.traverse(self.app.render)

        return task.cont
