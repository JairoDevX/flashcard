
Apps:
- `accounts`: auth, perfil, preferências de estudo (novas/dia, etc.)
- `decks`: decks, cards, tags
- `study`: sessão de estudo, fila diária, engine SRS
- `analytics`: métricas, relatórios e gráficos

---

## 5) Modelagem de dados (essencial)

### Deck
- `id`
- `user` (FK)
- `name`
- `description`
- `created_at`

### Card
- `id`
- `deck` (FK)
- `front` (text)
- `back` (text)
- `tags` (text/json opcional)
- `created_at`
- `updated_at`

### CardSchedule (SRS)
Armazena o estado do cartão para repetição espaçada.
- `card` (OneToOne)
- `ease_factor` (float) — ex: inicia em 2.5
- `interval_days` (int) — dias
- `repetitions` (int) — quantas vezes acertou em sequência
- `due_at` (date/datetime) — próxima revisão
- `lapses` (int) — quantas vezes “caiu” por erro
- `state` (choice) — NEW | LEARNING | REVIEW

### ReviewLog
Registro de respostas para métricas.
- `user`
- `card`
- `reviewed_at`
- `rating` (0–3 ou 0–5)
- `time_spent_ms` (opcional)
- `was_correct` (bool)

### UserStudySettings
- `user`
- `new_cards_per_day` (int)
- `max_reviews_per_day` (int ou null)
- `timezone`
- `session_order` (ex: revisões primeiro)

---

## 6) Fluxo de estudo (UX)

1. Dashboard:
   - “Você tem **12 revisões** e **5 novas** hoje”
   - Botão **Começar**
2. Sessão:
   - Mostra frente
   - Clique “Ver resposta”
   - Botões de avaliação:
     - **Errei**
     - **Difícil**
     - **Bom**
     - **Fácil**
3. Final:
   - Resumo: acertos, tempo, cartões agendados para amanhã

---

## 7) Algoritmo de repetição espaçada (SM-2 simplificado)

### Rating (recomendado)
- 0 = Errei
- 1 = Difícil
- 2 = Bom
- 3 = Fácil

### Regras (exemplo)
- Se **Errei (0)**:
  - `repetitions = 0`
  - `interval_days = 1` (ou 0 para reaparecer na sessão)
  - `ease_factor = max(1.3, ease_factor - 0.2)`
  - `due_at = hoje + 1 dia` (ou reintroduzir “reforço” na sessão)
- Se **Difícil (1)**:
  - `ease_factor = max(1.3, ease_factor - 0.15)`
  - `interval_days = max(1, round(interval_days * 1.2))`
- Se **Bom (2)**:
  - `ease_factor = max(1.3, ease_factor - 0.05)`
  - `interval_days = 1` se `repetitions == 0`, `6` se `repetitions == 1`, senão `round(interval_days * ease_factor)`
  - `repetitions += 1`
- Se **Fácil (3)**:
  - `ease_factor = ease_factor + 0.1`
  - `interval_days = 2` se `repetitions == 0`, `7` se `repetitions == 1`, senão `round(interval_days * (ease_factor + 0.15))`
  - `repetitions += 1`

> Você pode evoluir depois para **FSRS** (mais moderno), mas o SM-2 já entrega excelente resultado no MVP.

---

## 8) Geração da fila diária (Daily Queue)

### Regras sugeridas
- `due_cards`: todos com `due_at <= hoje`
- `new_cards`: cards sem `CardSchedule` ou `state=NEW` limitados por `new_cards_per_day`
- `learning_cards`: errados hoje (reforço) com prioridade

**Ordem recomendada**
1. Learning (reforço)
2. Due (revisões vencidas)
3. New (novas)

### Evitar repetição ruim
- Embaralhar por deck/tag
- Evitar dois cards “muito parecidos” seguidos (futuro)

---

## 9) Endpoints / Rotas (Django)

### Pages
- `/` Dashboard
- `/decks/` Lista decks
- `/decks/<id>/` Deck detalhado
- `/decks/<id>/cards/new` Criar card
- `/study/` Iniciar sessão
- `/study/session` Tela de estudo (HTMX)
- `/analytics/` Métricas

### Ações (HTMX ou POST)
- `POST /study/answer` (card_id, rating, time_spent)

---

## 10) UI moderna (Tailwind + HTMX)

Componentes:
- Card (flashcard) com animação de flip
- Botões grandes (Errei/Difícil/Bom/Fácil)
- Barra de progresso: “7/20”
- Micro-feedback: “Próxima revisão em 6 dias”

Padrões:
- Mobile-first
- Acessibilidade (botões grandes, contrastes bons)
- Atalhos no teclado (1-4)

---

## 11) Segurança e qualidade

- CSRF habilitado (Django padrão).
- Permissões: usuário só acessa seus decks/cards.
- Validação: front/back.
- Logs de revisão para auditoria e métricas.

Testes:
- Unit test do SRS engine (muito importante)
- Teste de fila diária
- Teste de permissões

---

## 12) Setup (dev)

### Requisitos
- Python 3.11+
- Node (para Tailwind) opcional
- Postgres (opcional no dev)

### Instalação (exemplo)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
