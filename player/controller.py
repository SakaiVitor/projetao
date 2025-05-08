from direct.showbase.ShowBaseGlobal import globalClock
from panda3d.core import Vec3, WindowProperties


class PlayerController:
    def __init__(self, app):
        self.app = app
        self.moving = True
        self.speed = 10
        self.mouse_sensitivity = 0.2
        self.prev_mouse_pos = None
        self.pitch = 0.0  # ângulo de inclinação da cabeça
        # Representação visual do jogador
        self.actor = self.app.loader.loadModel("models/misc/rgbCube")
        self.actor.setScale(0.5)
        self.actor.setColor(0, 1, 1, 1)
        self.actor.setPos(0, 0, 1)
        self.actor.reparentTo(self.app.render)

        # Câmera presa ao corpo do jogador
        self.app.disableMouse()
        self.app.camera.reparentTo(self.actor)
        self.app.camera.setPos(0, 0, 1.5)  # Altura da cabeça

        # Entrada de controle
        self.keys = {"w": False, "s": False, "a": False, "d": False}
        self.setup_controls()

        # Aplica travamento do mouse depois da janela estar pronta
        self.app.taskMgr.doMethodLater(0.1, lambda task: self.lock_mouse() or task.done, "lockMouse")

        # Task principal de atualização
        self.app.taskMgr.add(self.update, "PlayerControllerUpdate")

    def setup_controls(self):
        for key in self.keys:
            self.app.accept(key, self.set_key, [key, True])
            self.app.accept(f"{key}-up", self.set_key, [key, False])
        self.app.accept("enter", self.toggle_input)

    def set_key(self, key, value):
        self.keys[key] = value

    def toggle_input(self):
        self.moving = not self.moving
        print("Modo de entrada de texto ativado" if not self.moving else "Movimento reativado")

    def lock_mouse(self):
        props = WindowProperties()
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_relative)  # Ideal para FPS
        self.app.win.requestProperties(props)

    def update(self, task):
        dt = globalClock.getDt()
        if not self.moving or not self.app.mouseWatcherNode.hasMouse():
            return task.cont

        # MOUSE LOOK
        mpos = self.app.win.getPointer(0)
        win_cx = self.app.win.getXSize() // 2
        win_cy = self.app.win.getYSize() // 2
        dx = mpos.getX() - win_cx
        dy = mpos.getY() - win_cy

        # Horizontal (gira o corpo)
        self.actor.setH(self.actor.getH() - dx * self.mouse_sensitivity)

        # Vertical (inclina a câmera)
        self.pitch -= dy * self.mouse_sensitivity
        self.pitch = max(-89, min(89, self.pitch))  # limita o ângulo
        self.app.camera.setP(self.pitch)

        # Reset cursor ao centro
        self.app.win.movePointer(0, win_cx, win_cy)

        # MOVIMENTO COM WASD
        direction = Vec3(0, 0, 0)
        if self.keys["w"]:
            direction += Vec3(0, 1, 0)
        if self.keys["s"]:
            direction += Vec3(0, -1, 0)
        if self.keys["a"]:
            direction += Vec3(-1, 0, 0)
        if self.keys["d"]:
            direction += Vec3(1, 0, 0)

        if direction.length() > 0:
            direction.normalize()
            world_dir = self.actor.getQuat().xform(direction)
            self.actor.setPos(self.actor.getPos() + world_dir * self.speed * dt)

        return task.cont
