from direct.gui.DirectGui import DirectEntry, OnscreenText, DirectFrame
from direct.gui import DirectGuiGlobals as DGG
from panda3d.core import TextNode, TransparencyAttrib
from direct.interval.IntervalGlobal import LerpFunc

class HUD:
    def __init__(self, app):
        self.app = app
        self.entry = None
        self.status = OnscreenText(text="", pos=(0, 0.85), scale=0.05, mayChange=True)
        self.bg_frame = None
        self.instruction = None
        self.placeholder = None

    def show_prompt(self):
        if self.entry:
            return

        self.app.player_controller.moving = False

        def fade_in(alpha):
            self.bg_frame.setColor(0, 0, 0, alpha * 0.7)
            self.prompt_frame.setColor(1, 1, 1, alpha)
            self.entry['text_fg'] = (0, 0, 0, alpha)
            self.placeholder.setColor(0.5, 0.5, 0.5, alpha)
            self.instruction.setColor(1, 1, 1, alpha)

        self.fade_in_interval = LerpFunc(fade_in, fromData=0.0, toData=1.0, duration=0.5)
        self.fade_in_interval.start()

        self.bg_frame = DirectFrame(frameColor=(0, 0, 0, 0.85), frameSize=(-2, 2, -2, 2), pos=(0, 0, 0), sortOrder=0)
        self.bg_frame.setTransparency(TransparencyAttrib.MAlpha)

        self.prompt_frame = DirectFrame(frameColor=(0.25, 0.25, 0.35, 0.9), frameSize=(-1.0, 1.0, -0.1, 0.1),
                                        pos=(0, 0, 0.8), borderWidth=(0.01, 0.01), relief=DGG.GROOVE)

        self.entry = DirectEntry(text="", scale=0.06, pos=(-0.95, 0, 0.8), frameColor=(0, 0, 0, 0),
                                 text_fg=(0, 0, 0, 1), numLines=1, focus=1, width=30, command=self.submit_prompt,
                                 text_align=TextNode.ALeft)
        self.entry.bind(DGG.TYPE, self._on_type)

        self.placeholder = OnscreenText(text="A chave está em suas palavras...", pos=(-0.9, 0.8), scale=0.045,
                                        fg=(0.7, 0.7, 0.8, 0.7), align=TextNode.ALeft, mayChange=True)

        self.instruction = OnscreenText(text="ENTER para enviar • TAB para cancelar", pos=(0.2, 0.75), scale=0.04,
                                        fg=(0.7, 0.7, 0.8, 0.8), align=TextNode.ALeft)

    def _on_type(self, *args):
        if self.placeholder:
            text = self.entry.get()
            self.placeholder.hide() if text else self.placeholder.show()

    def close_prompt(self):
        if not self.entry:
            return

        def fade_out(alpha):
            self.bg_frame.setColorScale(0, 0, 0, alpha * 0.7)
            self.prompt_frame.setColorScale(1, 1, 1, alpha)
            self.entry['text_fg'] = (0, 0, 0, alpha)
            self.placeholder.setColor(0.5, 0.5, 0.5, alpha)
            self.instruction.setColor(1, 1, 1, alpha)

        def cleanup():
            for element in [self.entry, self.bg_frame, self.instruction, self.placeholder, self.prompt_frame]:
                if element:
                    element.destroy()
            self.entry = self.bg_frame = self.instruction = self.placeholder = self.prompt_frame = None
            self.app.player_controller.moving = True

        self.fade_out_interval = LerpFunc(fade_out, fromData=1.0, toData=0.0, duration=0.3,
                                          blendType='easeInOut', name='fadeOutPrompt')
        self.fade_out_interval.setDoneEvent('fadeOutDone')
        self.app.acceptOnce('fadeOutDone', cleanup)
        self.fade_out_interval.start()

    def submit_prompt(self, text):
        print("📨 [HUD] submit_prompt chamado com:", text)
        self.close_prompt()
        self.app.loop.create_task(self.app.placer.handle_prompt_submission(text))

    def is_prompt_visible(self):
        return self.entry is not None
