from panda3d.core import NodePath, LVector3f, Filename, TextNode, BitMask32, TransparencyAttrib
from pathlib import Path
from direct.task import Task
import random
from math import sin
from prompt.quiz_system import QuizSystem
from sentence_transformers import util
from direct.interval.LerpInterval import LerpColorScaleInterval
from direct.interval.MetaInterval import Sequence
from direct.interval.FunctionInterval import Func


class NPCManager:
    def __init__(self, app):
        self.app = app
        self.npc_dir = Path("assets/models/npcs")
        self.npc_models = list(self.npc_dir.glob("*.obj"))
        self.spawned_models = set()
        self.quiz_system = QuizSystem()
        self.npcs: list[NodePath] = []

        self.qa_triples = [
            {
                "question": "Sou um gênio que sai de uma lâmpada e realiza três desejos. Quem sou eu?",
                "answers": ["Gênio da Lâmpada", "Genie", "Gênio", "Gênio do Aladdin"],
                "threshold": 0.65
            },
            {
                "question": "Com capa preta, defendo Gotham à noite. Quem sou?",
                "answers": ["Batman", "O Cavaleiro das Trevas", "Bruce Wayne"],
                "threshold": 0.7
            },
            {
                "question": "Sou pequeno, verde, mestre da Força. Quem sou?",
                "answers": ["Yoda", "Mestre Yoda"],
                "threshold": 0.7
            },
            {
                "question": "Salvei vidas e enfrentei horrores no Titanic. Quem sou?",
                "answers": ["Jack", "Jack Dawson", "Leonardo DiCaprio"],
                "threshold": 0.68
            },
            {
                "question": "Comandante de um navio estelar, exploro a fronteira final. Quem sou?",
                "answers": ["Capitão Kirk", "James T. Kirk", "Kirk"],
                "threshold": 0.7
            },
            {
                "question": "Sou feito de um metal poderoso e carrego um escudo com uma estrela. Quem sou?",
                "answers": ["Capitão América", "Steve Rogers"],
                "threshold": 0.7
            },
            {
                "question": "Com uma varinha e uma cicatriz na testa, enfrento o mal. Quem sou?",
                "answers": ["Harry Potter"],
                "threshold": 0.75
            },
            {
                "question": "Sou um artefato com poder de controlar o tempo. Quem sou?",
                "answers": ["Ampulheta", "Ampulheta do Tempo", "Time Turner"],
                "threshold": 0.6
            },
            {
                "question": "Meu criador é Tony Stark. Sou uma armadura com inteligência. Quem sou?",
                "answers": ["Homem de Ferro", "Iron Man", "Tony Stark"],
                "threshold": 0.7
            },
            {
                "question": "Sou uma bola dourada veloz usada em um esporte mágico. Quem sou?",
                "answers": ["Pomo de Ouro", "Golden Snitch"],
                "threshold": 0.65
            },
        ]

    def spawn_npc(self, *, position, facing_direction="south", door_node=None) -> NodePath:
        if not self.npc_models:
            print("Nenhum modelo .obj encontrado em assets/models/npcs")
            return None

        available_models = [m for m in self.npc_models if m not in self.spawned_models]
        if not available_models:
            self.spawned_models.clear()
            available_models = list(self.npc_models)

        model_path = random.choice(available_models)
        self.spawned_models.add(model_path)

        npc = self.app.loader.loadModel(Filename.from_os_specific(str(model_path)))
        npc.setScale(3)

        heading_map = {
            "north": 0, "east": 90, "south": 180, "west": 270,
        }
        npc.setH(heading_map.get(facing_direction, 0))
        npc.setPos(position)
        npc.reparentTo(self.app.render)

        min_bound, _ = npc.getTightBounds()
        if min_bound:
            npc.setZ(position.getZ() - min_bound.getZ() - 0.05)

        def breathing_task(task, node=npc):
            scale = 2 + 0.02 * sin(task.time * 2)
            node.setScale(scale)
            return Task.cont

        self.app.taskMgr.add(breathing_task, f"breathing-task-{id(npc)}")

        qa = random.choice(self.qa_triples)
        self.quiz_system.definir_enigma(qa["question"], qa["answers"])
        npc.setPythonTag("threshold", qa["threshold"])

        speech_node_text = TextNode("npc-text")
        speech_node_text.setText(qa["question"])
        speech_node_text.setAlign(TextNode.ACenter)
        speech_node_text.setTextColor(1, 1, 1, 1)
        speech_node_text.setCardColor(0, 0, 0, 1)
        speech_node_text.setCardAsMargin(0.3, 0.3, 0.2, 0.2)
        speech_node_path = NodePath(speech_node_text.generate())
        speech_node_path.setScale(0.2)
        speech_node_path.setBillboardAxis()
        speech_node_path.setLightOff()
        speech_node_path.setDepthWrite(False)
        speech_node_path.setDepthTest(False)
        speech_node_path.reparentTo(self.app.render)
        speech_node_path.hide()

        def update_speech(task, npc=npc, node=speech_node_path):
            if not npc or not node:
                return Task.done
            node.setPos(npc.getX(), npc.getY(), npc.getZ() + 1)
            player_node = getattr(self.app.player_controller, "node", None)
            if player_node:
                distance = (npc.getPos(self.app.render) - player_node.getPos(self.app.render)).length()
                node.show() if distance < 10.0 else node.hide()
            return Task.cont

        self.app.taskMgr.add(update_speech, f"text-follow-{id(npc)}")

        npc.setPythonTag("door_node", door_node)
        npc.setPythonTag("answers", qa["answers"])
        npc.setPythonTag("threshold", qa["threshold"])

        self.npcs.append(npc)
        return npc

    def on_correct_response(self, door_node: NodePath):
        print("✅ Resposta correta! Procurando portas para remoção...")

        if door_node.isEmpty():
            print("⚠️ Porta inválida (NodePath vazio).")
            return

        door_name = door_node.getName()
        print(f"🟨 Encontrada porta: {door_name}")

        # Aplica transparência
        door_node.setTransparency(TransparencyAttrib.MAlpha)
        door_node.setColorScale(1, 1, 1, 1)

        fade = LerpColorScaleInterval(
            door_node,
            duration=1.0,
            startColorScale=(1, 1, 1, 1),
            colorScale=(1, 1, 1, 0)
        )

        def finalizar():
            print(f"🚪 Fade-out concluído. Removendo {door_name}")
            door_node.detachNode()  # remove da árvore, mas mantém referência
            door_node.removeNode()  # apaga de verdade

            # Checagem de segurança: tenta encontrar outra porta com mesmo nome
            still_exists = self.app.render.find("**/porta_sala")
            if not still_exists.isEmpty():
                print(f"❌ Ainda existe: {still_exists}, forçando remoção final...")
                still_exists.removeNode()
            else:
                print("🚪 Porta removida com sucesso.")

        Sequence(fade, Func(finalizar)).start()
        self.app.render.ls()  # debug opcional

    def try_answer(self, resposta: str, npc: NodePath):
        if self.quiz_system.avaliar_resposta(resposta, npc.getPythonTag("threshold")):
            door = npc.getPythonTag("door_node")
            if door and not door.isEmpty():
                self.on_correct_response(door)
            return True
        print("❌ Resposta incorreta ou abaixo do limiar.")
        return False

    def try_prompt_nearby(self, prompt: str, obj_pos, radius: float = 2.0) -> bool:
        model = self.quiz_system.model
        for npc in self.npcs:
            if (npc.getPos(self.app.render).getXy() - obj_pos.getXy()).length() > radius:
                continue

            answers = npc.getPythonTag("answers")
            threshold = npc.getPythonTag("threshold")

            emb_p = model.encode(prompt, convert_to_tensor=True)
            emb_a = model.encode(answers, convert_to_tensor=True)
            score = util.cos_sim(emb_p, emb_a).max().item()

            if score >= threshold:
                door = npc.getPythonTag("door_node")
                if door and not door.isEmpty():
                    self.on_correct_response(door)
                    print(f"✅ Porta da sala aberta! (score {score:.2f})")
                return True
        return False
