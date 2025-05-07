class Engine:
    def __init__(self, app):
        self.app = app
        self.setup_display()
        self.setup_input()

    def setup_display(self):
        self.app.win.setClearColor((0.1, 0.1, 0.1, 1))
        self.app.setFrameRateMeter(True)

    def setup_input(self):
        self.app.accept("escape", self.app.userExit)
