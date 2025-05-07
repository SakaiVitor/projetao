# prompt/prompt_manager.py

import aiohttp
import asyncio
import pathlib
import tempfile

API_URL = "http://127.0.0.1:8000"

class PromptManager:
    def __init__(self):
        self.loop = asyncio.get_event_loop()

    async def request_model(self, prompt: str) -> pathlib.Path:
        async with aiohttp.ClientSession() as s:
            # Envia o prompt
            resp = await s.post(f"{API_URL}/generate", json={"prompt": prompt})
            jid = (await resp.json())["job_id"]

            # Espera o modelo ser gerado
            while True:
                result = await (await s.get(f"{API_URL}/result/{jid}")).json()
                if result["status"] == "finished":
                    break
                await asyncio.sleep(1)

            # Baixa o arquivo .obj
            tmp_dir = pathlib.Path(tempfile.mkdtemp())
            obj_path = tmp_dir / "mesh.obj"
            obj_path.write_bytes(await (await s.get(API_URL + result["obj"])).read())

            return obj_path

    def generate_model(self, prompt: str) -> pathlib.Path:
        return self.loop.run_until_complete(self.request_model(prompt))
