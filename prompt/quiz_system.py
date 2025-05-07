# prompt/quiz_system.py

from sentence_transformers import SentenceTransformer, util


class QuizSystem:
    def __init__(self):
        # Você pode trocar por outro modelo mais robusto, se desejar
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.enigma_atual = None
        self.respostas_validas = []

    def definir_enigma(self, texto: str, respostas: list[str]):
        """Define um novo enigma e suas possíveis soluções"""
        self.enigma_atual = texto
        self.respostas_validas = respostas

    def avaliar_resposta(self, prompt: str, threshold: float = 0.6) -> bool:
        """Compara semanticamente o prompt com as respostas válidas"""
        if not self.respostas_validas:
            return False

        emb_prompt = self.model.encode(prompt, convert_to_tensor=True)
        emb_validas = self.model.encode(self.respostas_validas, convert_to_tensor=True)

        scores = util.cos_sim(emb_prompt, emb_validas)
        max_score = scores.max().item()

        return max_score >= threshold

    def obter_melhor_correspondencia(self, prompt: str):
        """Retorna a melhor correspondência e seu score"""
        if not self.respostas_validas:
            return None, 0.0

        emb_prompt = self.model.encode(prompt, convert_to_tensor=True)
        emb_validas = self.model.encode(self.respostas_validas, convert_to_tensor=True)
        scores = util.cos_sim(emb_prompt, emb_validas)

        best_idx = scores.argmax().item()
        return self.respostas_validas[best_idx], scores[0, best_idx].item()
