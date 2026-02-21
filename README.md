# 📚 FlashCards — Sistema de Estudo com Repetição Espaçada

Aplicativo web de flashcards com algoritmo SM-2, geração por IA, e autenticação JWT.

---

## 🚀 Instalação Rápida

```bash
# 1. Instalar dependências
pip3 install -r requirements.txt

# 2. Aplicar migrações
python3 manage.py migrate

# 3. Criar planos padrão
python3 manage.py seed_plans

# 4. Criar superusuário (admin)
python3 manage.py createsuperuser

# 5. Iniciar servidor
python3 manage.py runserver
```

Acesse: http://localhost:8000

---

## 👥 Criando Usuários

### Via Interface Web
Acesse `/accounts/register/` para criar uma conta. O plano **Grátis** é atribuído automaticamente.

### Via Django Admin
1. Acesse `http://localhost:8000/admin/`
2. Faça login com o superusuário
3. Vá em **Autenticação e Autorização → Usuários → Adicionar usuário**
4. Preencha usuário e senha → Salvar

Para tornar um usuário staff (acesso ao admin):
- Na tela do usuário: marque **Membro da equipe** e **Status de superusuário** se necessário

### Via Django Shell
```python
python3 manage.py shell

# Criar usuário comum
from django.contrib.auth.models import User
user = User.objects.create_user(
    username='joao',
    email='joao@email.com',
    password='senha_segura_123'
)

# Criar superusuário
admin = User.objects.create_superuser(
    username='admin',
    email='admin@email.com',
    password='admin_pass_123'
)
```

### Via Management Command
```bash
# Superusuário interativo
python3 manage.py createsuperuser

# Criar usuário em script (não interativo)
python3 manage.py shell -c "
from django.contrib.auth.models import User
from accounts.models import UserStudySettings, UserSubscription, Plan
user = User.objects.create_user('usuario', 'email@ex.com', 'senha123')
UserStudySettings.objects.create(user=user)
plan = Plan.objects.get(slug='free')
UserSubscription.objects.create(user=user, plan=plan)
print('Usuário criado:', user.username)
"
```

---

## 💳 Criando e Gerenciando Planos

### Planos Padrão
Execute o comando de seed para criar os 3 planos padrão (Grátis / Pro / Premium):

```bash
python3 manage.py seed_plans
```

### Via Django Admin
1. Acesse `http://localhost:8000/admin/`
2. Vá em **Accounts → Plans → Adicionar plan**
3. Preencha os campos:
   - **Name**: Nome do plano (ex: "Business")
   - **Slug**: identificador único (ex: `business`) — gerado automaticamente
   - **Price monthly / yearly**: preços
   - **Max decks / Max cards**: limites (deixe em branco para ilimitado)
   - **Max cards per day**: cards por sessão
   - **Ai generation**: se o plano inclui geração por IA
   - **Is default**: marque **apenas um** plano como padrão (atribuído a novos usuários)

### Via Django Shell
```python
python3 manage.py shell

from accounts.models import Plan

# Criar plano customizado
plan = Plan.objects.create(
    name="Business",
    slug="business",
    description="Para times e empresas",
    price_monthly=99.90,
    price_yearly=899.90,
    max_decks=None,       # ilimitado
    max_cards=None,       # ilimitado
    max_cards_per_day=1000,
    ai_generation=True,
    priority_support=True,
    sort_order=3,
)
print(f"Plano criado: {plan}")
```

### Atribuindo Plano a um Usuário
```python
python3 manage.py shell

from django.contrib.auth.models import User
from accounts.models import Plan, UserSubscription
from django.utils import timezone
from datetime import timedelta

user = User.objects.get(username='joao')
plan = Plan.objects.get(slug='pro')

# Criar ou atualizar assinatura
sub, created = UserSubscription.objects.update_or_create(
    user=user,
    defaults={
        'plan': plan,
        'is_active': True,
        'expires_at': timezone.now() + timedelta(days=30),  # 30 dias
    }
)
print(f"Assinatura: {sub}")
```

### Assinatura sem expiração (vitalícia)
```python
UserSubscription.objects.update_or_create(
    user=user,
    defaults={'plan': plan, 'is_active': True, 'expires_at': None}
)
```

---

## 🔐 Autenticação JWT

### Como Funciona
O app usa **autenticação dupla**:
- **Sessão** (para o site web / HTMX) — cookie `sessionid`
- **JWT** (para API / mobile) — cookies httpOnly `access_token` e `refresh_token`

Ambos são emitidos automaticamente no login.

### Endpoints da API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/auth/token/` | Obter tokens JWT |
| `POST` | `/api/auth/token/refresh/` | Renovar access token |
| `GET`  | `/api/auth/me/` | Dados do usuário autenticado |

### Obter Token (curl)
```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "seu_usuario", "password": "sua_senha"}'
```

Resposta:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "username": "seu_usuario",
    "email": "email@ex.com"
  }
}
```

### Usar Token nas Requests
```bash
# Bearer token no header
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/auth/me/

# Renovar access token expirado
curl -X POST http://localhost:8000/api/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'
```

### Configurações JWT (settings.py)
```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),   # Expira em 1h
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),   # Expira em 7 dias
    "ROTATE_REFRESH_TOKENS": True,                 # Gera novo refresh a cada uso
    "BLACKLIST_AFTER_ROTATION": True,              # Invalida refresh antigo
    "AUTH_COOKIE_HTTP_ONLY": True,                 # httpOnly (seguro contra XSS)
    "AUTH_COOKIE_SECURE": False,                   # True em produção (HTTPS)
}
```

---

## 🤖 Geração de Cards por IA

Para usar a geração de cards por IA (plano Pro/Premium):

1. Obtenha uma chave de API da Anthropic: https://console.anthropic.com
2. Configure a variável de ambiente:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```
3. Na tela do deck, clique em **"✨ Gerar com IA"**
4. Cole um texto ou descreva um tópico
5. Revise e salve os cards gerados

O modelo usado é `claude-haiku-4-5` (mais rápido e econômico).

---

## 🗂️ Estrutura do Projeto

```
flashcard/
├── accounts/          # Autenticação, perfil, planos
│   ├── management/commands/seed_plans.py
│   ├── models.py      # UserStudySettings, Plan, UserSubscription
│   ├── views.py       # Login JWT, API endpoints
│   └── admin.py       # Admin customizado para planos
├── decks/             # CRUD de decks e cards
│   └── models.py      # Deck (com idiomas), Card (com tipo cloze)
├── study/             # Sessões de estudo
│   ├── engine.py      # Algoritmo SM-2
│   └── views.py       # HTMX study flow
├── analytics/         # Estatísticas e progresso
├── templates/         # Templates HTML
└── static/            # CSS, JS
```

---

## 🌱 Variáveis de Ambiente (Produção)

Crie um arquivo `.env` na raiz:

```env
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=False
ALLOWED_HOSTS=seudominio.com,www.seudominio.com
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgres://user:pass@host:5432/dbname
```

---

## 📋 Comandos Úteis

```bash
# Criar migrações após alterar models
python3 manage.py makemigrations
python3 manage.py migrate

# Shell interativo
python3 manage.py shell

# Seed de planos padrão
python3 manage.py seed_plans

# Coletar arquivos estáticos (produção)
python3 manage.py collectstatic

# Checar problemas
python3 manage.py check
```
