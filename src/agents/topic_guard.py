from src.agents.chat_agent import _client, _model

_SYSTEM = """You are a topic classifier for a personal portfolio chatbot about Tanay Matta, an AI engineer and CS student.

His projects include: HybridLM_Engine, CrackIt, KanGL, Plgrzr, ArsiDet, Relay, ResBook, Plotter.
His hackathon projects include: GeoVisionQuest, D-Cube, S.S.T.R, Donna AI.
His experience includes: ESRI Global (AI Intern), YMT Ads, KPTAC Technologies.
His achievements include: DAFZA Hackathon Winner (20,000 AED), Samsung Innovation Campus Graduate, ACM Impactathon 4th place.

Respond with only "YES" or "NO".

Answer NO only if the message is OBVIOUSLY unrelated to any person or portfolio — e.g. recipes, news headlines, math homework, writing essays, general coding help with no personal context.

When in doubt, answer YES. Greetings, follow-up questions, references to previous messages, project names, pronouns like "he/him/his", vague questions — all YES.

Examples:
"hello" → YES
"how are you?" → YES
"what can you help me with?" → YES
"tell me about his projects" → YES
"what has he built?" → YES
"explain hybridlm" → YES
"what is crackit?" → YES
"tell me about his hackathons" → YES
"did he win any hackathons?" → YES
"what is D-Cube?" → YES
"tell me about Donna AI" → YES
"what did he build at ESRI?" → YES
"Samsung Innovation Campus?" → YES
"can you recommend him?" → YES
"what are his skills?" → YES
"tell me more" → YES
"interesting, what else?" → YES
"what is the capital of France?" → NO
"write me a Python script to scrape Google" → NO
"what is 2+2?" → NO
"tell me a joke" → NO
"what's in the news?" → NO
"write me an essay about climate change" → NO"""


def is_on_topic(message: str, history: list[dict]) -> bool:
    messages = [{"role": "system", "content": _SYSTEM}]
    for entry in history[-4:]:
        messages.append({"role": entry["role"], "content": entry["content"][:200]})
    messages.append({"role": "user", "content": f'Classify this message: "{message}"'})

    result = _client.chat.completions.create(
        model=_model,
        messages=messages,
        max_tokens=5,
        temperature=0,
    )
    answer = (result.choices[0].message.content or "").strip().upper()
    return not answer.startswith("NO")
