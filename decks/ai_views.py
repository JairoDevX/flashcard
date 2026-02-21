"""
AI-powered card generation using Claude (Anthropic).
Requires ANTHROPIC_API_KEY in environment.
"""
import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from .models import Card, Deck


SYSTEM_PROMPT = """Você é um especialista em criação de flashcards educacionais.
Dado um texto ou tópico, gere flashcards no formato JSON.
Responda APENAS com JSON válido, sem nenhum texto adicional.

Formato obrigatório:
{
  "cards": [
    {"card_type": "normal", "front": "Pergunta ou conceito", "back": "Resposta ou definição"},
    {"card_type": "cloze", "front": "A capital do Brasil é {{Brasília}}", "back": "Brasília é a capital federal do Brasil desde 1960."}
  ]
}

Regras:
- Gere entre 5 e 15 cards dependendo do conteúdo
- Cards normais: frente com pergunta clara, verso com resposta concisa
- Cards cloze: use {{palavra}} para marcar a lacuna no texto da frente
- Misture tipos para variedade
- Seja direto e objetivo
- Adapte o idioma ao texto de entrada"""


@login_required
def ai_generate(request, deck_pk):
    deck = get_object_or_404(Deck, pk=deck_pk, user=request.user)

    if not settings.ANTHROPIC_API_KEY:
        messages.error(
            request,
            "Chave da API Anthropic não configurada. "
            "Defina ANTHROPIC_API_KEY no ambiente."
        )
        return redirect("deck_detail", pk=deck_pk)

    # Check if user's plan allows AI generation
    subscription = getattr(request.user, "subscription", None)
    if subscription and hasattr(subscription, "plan"):
        if not subscription.plan.ai_generation:
            messages.error(
                request,
                f"Geração por IA não está disponível no plano {subscription.plan.name}. "
                "Faça upgrade para o plano Pro ou Premium."
            )
            return redirect("deck_detail", pk=deck_pk)

    generated_cards = []
    error = None
    user_text = ""

    if request.method == "POST":
        action = request.POST.get("action")
        user_text = request.POST.get("text", "").strip()

        if action == "save_cards":
            # Save selected cards from the generated list
            saved = 0
            cards_json = request.POST.get("cards_json", "[]")
            try:
                card_list = json.loads(cards_json)
                selected_indices = request.POST.getlist("selected_cards")
                selected_indices = [int(i) for i in selected_indices]

                for idx in selected_indices:
                    if 0 <= idx < len(card_list):
                        c = card_list[idx]
                        Card.objects.create(
                            deck=deck,
                            card_type=c.get("card_type", "normal"),
                            front=c.get("front", ""),
                            back=c.get("back", ""),
                        )
                        saved += 1
            except (json.JSONDecodeError, ValueError, KeyError):
                messages.error(request, "Erro ao salvar cards. Tente novamente.")
                return redirect("ai_generate", deck_pk=deck_pk)

            messages.success(request, f"{saved} card{'s' if saved != 1 else ''} adicionado{'s' if saved != 1 else ''} ao deck!")
            return redirect("deck_detail", pk=deck_pk)

        elif action == "generate" and user_text:
            # Call Claude API
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

                response = client.messages.create(
                    model="claude-haiku-4-5",
                    max_tokens=2048,
                    system=SYSTEM_PROMPT,
                    messages=[
                        {
                            "role": "user",
                            "content": f"Gere flashcards baseados neste conteúdo:\n\n{user_text}"
                        }
                    ],
                )

                raw = response.content[0].text.strip()

                # Extract JSON even if wrapped in markdown code blocks
                if "```" in raw:
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]

                data = json.loads(raw)
                generated_cards = data.get("cards", [])

                if not generated_cards:
                    error = "Nenhum card foi gerado. Tente com um texto mais detalhado."

            except json.JSONDecodeError:
                error = "Resposta da IA em formato inválido. Tente novamente."
            except Exception as e:
                error = f"Erro ao chamar a IA: {str(e)}"

    return render(request, "decks/ai_generate.html", {
        "deck": deck,
        "generated_cards": generated_cards,
        "cards_json": json.dumps(generated_cards),
        "user_text": user_text,
        "error": error,
        "has_api_key": bool(settings.ANTHROPIC_API_KEY),
    })
