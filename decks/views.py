from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CardForm, DeckForm
from .models import Card, Deck


# ─── Dashboard ───────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    from study.engine import get_daily_queue
    from study.models import CardSchedule, ReviewLog
    from accounts.models import UserStudySettings

    decks = Deck.objects.filter(user=request.user)
    queue = get_daily_queue(request.user)
    today = date.today()

    # Streak
    streak = 0
    d = today
    while True:
        if ReviewLog.objects.filter(user=request.user, reviewed_at__date=d).exists():
            streak += 1
            d -= timedelta(days=1)
        else:
            break

    settings, _ = UserStudySettings.objects.get_or_create(user=request.user)
    scheduled_ids = CardSchedule.objects.filter(
        card__deck__user=request.user
    ).values_list('card_id', flat=True)
    total_new = Card.objects.filter(deck__user=request.user).exclude(id__in=scheduled_ids).count()

    due_count = CardSchedule.objects.filter(
        card__deck__user=request.user,
        due_at__lte=today,
        state__in=[CardSchedule.STATE_REVIEW, CardSchedule.STATE_LEARNING],
    ).count()

    return render(request, 'dashboard.html', {
        'decks': decks,
        'queue_count': len(queue),
        'due_count': due_count,
        'new_count': min(total_new, settings.new_cards_per_day),
        'streak': streak,
    })


# ─── Deck CRUD ────────────────────────────────────────────────────────────────

@login_required
def deck_list(request):
    decks = Deck.objects.filter(user=request.user)
    return render(request, 'decks/list.html', {'decks': decks})


@login_required
def deck_detail(request, pk):
    deck = get_object_or_404(Deck, pk=pk, user=request.user)
    cards = deck.cards.all()
    return render(request, 'decks/detail.html', {'deck': deck, 'cards': cards})


@login_required
def deck_create(request):
    if request.method == 'POST':
        form = DeckForm(request.POST)
        if form.is_valid():
            deck = form.save(commit=False)
            deck.user = request.user
            deck.save()
            messages.success(request, 'Deck criado com sucesso!')
            return redirect('deck_detail', pk=deck.pk)
    else:
        form = DeckForm()
    return render(request, 'decks/deck_form.html', {'form': form, 'action': 'Criar'})


@login_required
def deck_edit(request, pk):
    deck = get_object_or_404(Deck, pk=pk, user=request.user)
    if request.method == 'POST':
        form = DeckForm(request.POST, instance=deck)
        if form.is_valid():
            form.save()
            messages.success(request, 'Deck atualizado!')
            return redirect('deck_detail', pk=deck.pk)
    else:
        form = DeckForm(instance=deck)
    return render(request, 'decks/deck_form.html', {'form': form, 'action': 'Editar', 'deck': deck})


@login_required
def deck_delete(request, pk):
    deck = get_object_or_404(Deck, pk=pk, user=request.user)
    if request.method == 'POST':
        deck.delete()
        messages.success(request, 'Deck excluído.')
        return redirect('deck_list')
    return render(request, 'decks/deck_confirm_delete.html', {'deck': deck})


# ─── Card CRUD ────────────────────────────────────────────────────────────────

@login_required
def card_create(request, deck_pk):
    deck = get_object_or_404(Deck, pk=deck_pk, user=request.user)
    if request.method == 'POST':
        form = CardForm(request.POST)
        if form.is_valid():
            card = form.save(commit=False)
            card.deck = deck
            card.save()
            messages.success(request, 'Card adicionado!')
            if 'add_another' in request.POST:
                return redirect('card_create', deck_pk=deck.pk)
            return redirect('deck_detail', pk=deck.pk)
    else:
        form = CardForm()
    return render(request, 'decks/card_form.html', {'form': form, 'deck': deck, 'action': 'Criar'})


@login_required
def card_edit(request, deck_pk, pk):
    deck = get_object_or_404(Deck, pk=deck_pk, user=request.user)
    card = get_object_or_404(Card, pk=pk, deck=deck)
    if request.method == 'POST':
        form = CardForm(request.POST, instance=card)
        if form.is_valid():
            form.save()
            messages.success(request, 'Card atualizado!')
            return redirect('deck_detail', pk=deck.pk)
    else:
        form = CardForm(instance=card)
    return render(request, 'decks/card_form.html', {'form': form, 'deck': deck, 'card': card, 'action': 'Editar'})


@login_required
def card_delete(request, deck_pk, pk):
    deck = get_object_or_404(Deck, pk=deck_pk, user=request.user)
    card = get_object_or_404(Card, pk=pk, deck=deck)
    if request.method == 'POST':
        card.delete()
        messages.success(request, 'Card excluído.')
        return redirect('deck_detail', pk=deck.pk)
    return render(request, 'decks/card_confirm_delete.html', {'deck': deck, 'card': card})


@login_required
def vocabulary_list(request):
    from study.models import CardSchedule

    search     = request.GET.get('q', '').strip()
    tag_filter = request.GET.get('tag', 'all')

    cards = Card.objects.filter(deck__user=request.user).select_related('deck').order_by('front')
    if search:
        cards = cards.filter(front__icontains=search) | cards.filter(back__icontains=search)
        cards = cards.order_by('front')

    schedules = {
        s.card_id: s
        for s in CardSchedule.objects.filter(card__deck__user=request.user)
    }

    all_tags = set()
    vocab    = []

    for card in cards:
        tags = card.get_tags_list()
        for t in tags:
            all_tags.add(t)

        if tag_filter not in ('all', 'hard', 'new') and tag_filter not in tags:
            continue

        sched = schedules.get(card.id)
        if sched:
            if sched.state == 'NEW':
                mastery, badge = 0, 'new'
            elif sched.state == 'LEARNING':
                mastery = min(sched.repetitions * 20, 50)
                badge   = 'learning'
            else:
                ef      = sched.ease_factor
                mastery = min(int(50 + (ef - 1.3) / (3.2 - 1.3) * 50), 100)
                badge   = 'learned' if mastery >= 70 else 'learning'
        else:
            mastery, badge = 0, 'new'

        if tag_filter == 'hard' and mastery >= 50:
            continue
        if tag_filter == 'new' and badge != 'new':
            continue

        vocab.append({
            'card': card, 'mastery': mastery, 'badge': badge,
            'tags': tags, 'stroke_offset': 100 - mastery,
        })

    if tag_filter == 'hard':
        vocab.sort(key=lambda x: x['mastery'])

    return render(request, 'decks/vocabulary.html', {
        'vocab':      vocab,
        'search':     search,
        'tag_filter': tag_filter,
        'all_tags':   sorted(all_tags),
        'total':      len(vocab),
    })
