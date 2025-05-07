from prompt.quiz_system import QuizSystem

qs = QuizSystem()
qs.definir_enigma("Como refrescar alguém com calor?", [
    "leque", "ventilador", "ar condicionado", "gelo", "sombra"
])

prompt = "ventilador azul"
ok = qs.avaliar_resposta(prompt)

print("Prompt:", prompt)
print("Aceito?", ok)

melhor, score = qs.obter_melhor_correspondencia(prompt)
print(f"Melhor correspondência: {melhor} (score: {score:.2f})")
