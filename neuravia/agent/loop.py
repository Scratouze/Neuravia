class AgentLoop:
    def __init__(self, goal, llm, max_steps=5):
        self.goal = goal
        self.llm = llm
        self.max_steps = max_steps

    def step(self, i):
        prompt = f"""
Tu es un agent. Objectif global :
{self.goal}

Étape {i}/{self.max_steps}.
Réponds avec une action simple et courte.
"""
        return self.llm(prompt)

    def run(self):
        history = []
        for i in range(1, self.max_steps + 1):
            out = self.step(i)
            print(f"[STEP {i}] {out.strip()}")
            history.append(out)
        return "\n".join(history)
