class PlayerController:
    def __init__(self, app):
        self.app = app
        self.moving = True
        self.setup_controls()

    def setup_controls(self):
        self.app.accept("enter", self.toggle_input)

    def toggle_input(self):
        self.moving = not self.moving
        print("Modo de entrada de texto ativado" if not self.moving else "Movimento reativado")

    def update(self):
        if not self.moving:
            return
        # Código de movimentação seria adicionado aqui
