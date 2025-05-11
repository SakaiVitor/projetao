from .pending_object import PendingObject


class ObjectPlacer:
    def __init__(self, app):
        self.app = app
        self.pending_objects = []

    async def handle_prompt_submission(self, prompt: str):
        obj = PendingObject(self.app, prompt)
        self.pending_objects.append(obj)
        await obj.start()

    def confirm_preview_under_cursor(self):
        # Confirma o último modelo não posicionado e pronto
        for obj in reversed(self.pending_objects):
            if obj.ready and not obj.placed:
                obj.confirm()
                break