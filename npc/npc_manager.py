from panda3d.core import NodePath, LVector3f, Filename, TextNode, BitMask32, TransparencyAttrib
from pathlib import Path
from direct.task import Task
import random
from math import sin
from direct.showbase.Audio3DManager import Audio3DManager
from core.load_wrapper import load_model_with_default_material
from prompt.quiz_system import QuizSystem
from sentence_transformers import util
from direct.interval.LerpInterval import LerpColorScaleInterval, LerpPosInterval
from direct.interval.MetaInterval import Sequence, Parallel
from direct.interval.FunctionInterval import Func


class NPCManager:
    def __init__(self, app):
        self.app = app
        self.npc_dir = Path("assets/models/npcs")
        self.npc_models = list(self.npc_dir.glob("*.obj"))
        self.spawned_models = set()
        self.quiz_system = QuizSystem()
        self.npcs: list[NodePath] = []
        self.audio3d = Audio3DManager(self.app.sfxManagerList[0], self.app.camera)
        self.som_porta = self.audio3d.loadSfx("assets/sounds/porta-abrindo.wav")

        self.qa_triples = [
            {
                "question": "Sou pequeno, verde, mestre da Força. Quem sou?",
                "answers": ["Yoda", "Mestre Yoda"],
                "threshold": 0.7
            },
            {
                "question": "Você compra para comer, mas jamais comerá.",
                "answers": ["Prato", "Talher", "Garfo", "Faca", "Colher"],
                "threshold": 0.7
            },
            {
                "question": "Se tiram minha pele, eu não choro, mas você, sim. Quem sou eu?",
                "answers": ["Cebola"],
                "threshold": 0.7
            },
            {
                "question": "Tenho cara, mas não tenho corpo. Quem sou eu?",
                "answers": ["Moeda", "Relógio", "Nota", "Máscara"],
                "threshold": 0.65
            },
            {
                "question": "Se sou aberta, espalho desgraça; se permaneço fechada, resta a esperança. O que sou?",
                "answers": ["Caixa de Pandora", "A Caixa de Pandora"],
                "threshold": 0.7
            },
            {
                "question": "Só posso ser empunhada pelo verdadeiro rei da Bretanha. O que sou?",
                "answers": ["Excalibur", "Espada Excalibur"],
                "threshold": 0.8
            },
            {
                "question": "Tenho chaves, mas não abro portas. Tenho notas, mas não sou dinheiro. Quem sou eu?",
                "answers": ["Piano", "Teclado"],
                "threshold": 0.7
            },
        ]

        self.frases_parabens = [
            "Muito bem! Você acertou!",
            "Resposta correta, pode avançar!",
            "Parabéns! Continue assim.",
            "Boa! A porta está aberta!",
            "Você é rápido no raciocínio!",
            "Excelente resposta!",
            "Mandou bem, siga em frente!"
        ]

        self.perguntas_restantes = self.qa_triples.copy()

    def spawn_npc(self, *, door_node=None, npc_scale=3.0) -> NodePath:
        if not self.npc_models:
            print("Nenhum modelo .obj encontrado em assets/models/npcs")
            return None

        available_models = [m for m in self.npc_models if m not in self.spawned_models]
        if not available_models:
            self.spawned_models.clear()
            available_models = list(self.npc_models)

        model_path = random.choice(available_models)
        self.spawned_models.add(model_path)

        npc = NodePath("npc")
        npc.reparentTo(self.app.render)

        model_node = load_model_with_default_material(self.app.loader, str(model_path))
        model_node.setName("model_node")
        model_node.reparentTo(npc)

        def breathing_task(task, node=model_node):
            amplitude = 0.01 * npc_scale
            scale = npc_scale + amplitude * sin(task.time * 2)
            node.setScale(scale)
            return Task.cont

        self.app.taskMgr.add(breathing_task, f"breathing-task-{id(npc)}")

        if not self.perguntas_restantes:
            print("[NPCManager] Todas as perguntas foram usadas. Reiniciando ciclo.")
            self.perguntas_restantes = self.qa_triples.copy()

        qa = random.choice(self.perguntas_restantes)
        self.perguntas_restantes.remove(qa)

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
        speech_node_path.reparentTo(npc)
        speech_node_path.setName("speech_node")  # identificável no .find()
        speech_node_path.hide()

        def update_speech(task, node=speech_node_path):
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

        door_node.setTransparency(TransparencyAttrib.MAlpha)
        door_node.setColorScale(1, 1, 1, 1)
        if self.som_porta:
            self.audio3d.attachSoundToObject(self.som_porta, door_node)
            self.som_porta.play()

        fade = LerpColorScaleInterval(
            door_node,
            duration=1.0,
            startColorScale=(1, 1, 1, 1),
            colorScale=(1, 1, 1, 0)
        )

        def finalizar():
            print(f"🚪 Fade-out concluído. Tentando remover {door_name}")
            if not door_node.isEmpty():
                # ❌ remover o colisor explicitamente
                col_np = door_node.find("**/+CollisionNode")
                if not col_np.isEmpty():
                    print(f"🗑️ Removendo colisor: {col_np.getName()}")
                    col_np.removeNode()

                door_node.hide()

                # Mostra frase de parabéns no NPC correspondente
                for npc in self.npcs:
                    if npc.getPythonTag("door_node") == door_node:
                        speech_node = npc.find("**/speech_node")
                        if not speech_node.isEmpty():
                            frase = random.choice(self.frases_parabens)
                            text_node = TextNode("npc-text")
                            text_node.setText(frase)
                            text_node.setAlign(TextNode.ACenter)
                            text_node.setTextColor(1, 1, 0.5, 1)
                            text_node.setCardColor(0, 0, 0, 1)
                            text_node.setCardAsMargin(0.3, 0.3, 0.2, 0.2)

                            new_node = NodePath(text_node.generate())
                            new_node.setScale(0.2)
                            new_node.setBillboardAxis()
                            new_node.setLightOff()
                            new_node.setDepthWrite(False)
                            new_node.setDepthTest(False)
                            new_node.setZ(2)  # ⬆️ sobe 2 unidades

                            speech_node.removeNode()
                            new_node.setName("speech_node")
                            new_node.reparentTo(npc)

                            # ⏳ remove depois de 3 segundos
                            def hide_text(task, node=new_node):
                                if not node.isEmpty():
                                    node.removeNode()
                                return Task.done

                            self.app.taskMgr.doMethodLater(3, hide_text, f"remove-speech-{id(new_node)}")
                        break

                door_node.removeNode()
                print("🚪 Porta removida com sucesso.")
            else:
                print("⚠️ door_node já estava vazio.")

            restantes = self.app.render.find_all_matches("**/porta_sala*")
            if restantes:
                print(f"❌ Ainda existem {restantes.get_num_paths()} portas com prefixo 'porta_sala':")
                for path in restantes:
                    print("↪️", path)

        # Detecta direção da porta com segurança
        parts = door_name.split("_")
        direction = parts[-1] if len(parts) >= 4 else "north"

        # Vetor de deslizamento perpendicular à parede
        slide_offset = {
            "north": LVector3f(2.5, 0, 0),
            "south": LVector3f(-2.5, 0, 0),
            "east": LVector3f(0, -2.5, 0),
            "west": LVector3f(0, 2.5, 0),
        }.get(direction, LVector3f(2.5, 0, 0))

        # Slide
        slide = LerpPosInterval(
            door_node,
            duration=1.0,
            pos=door_node.getPos() + slide_offset
        )

        # Fade-out
        fade = LerpColorScaleInterval(
            door_node,
            duration=1.0,
            startColorScale=(1, 1, 1, 1),
            colorScale=(1, 1, 1, 0)
        )

        # Executa em paralelo (ao mesmo tempo)
        Sequence(
            Parallel(fade, slide),
            Func(finalizar)
        ).start()

    def try_prompt_nearby(self, prompt: str, obj_pos, radius: float = 5) -> bool:
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
