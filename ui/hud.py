from direct.gui.DirectGui import DirectEntry, OnscreenText

class HUD:
    def __init__(self, app):
        self.app = app
        self.entry = None
        self.status = OnscreenText(text="", pos=(0, 0.9), scale=0.05, mayChange=True)

    def show_prompt(self):
        if not self.entry:
            self.entry = DirectEntry(text="", scale=0.05, pos=(-0.5, 0, 0),
                                     command=self.submit_prompt, focus=1)

    def submit_prompt(self, text):
        self.status.setText(f"Prompt enviado: {text}")
        self.entry.destroy()
        self.entry = None
