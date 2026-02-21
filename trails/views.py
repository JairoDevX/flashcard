import re
import random
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_htmx.http import HttpResponseClientRedirect
from django.urls import reverse

from .models import Trail, Lesson, LessonProgress
from decks.models import Card, Deck

LESSON_SIZE = 6
# Lições acima deste índice (base-1) entram em fase ativa (produção)
ACTIVE_PHASE_FROM = 7
LESSON_TITLES = [
    'Introdução', 'Fundamentos', 'Intermediário', 'Avançado',
    'Especialista', 'Mestre', 'Lendário', 'Supremo',
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_cloze_context(card):
    """Generate multiple-choice options for a cloze card (fase passiva)."""
    match = re.search(r'\{\{([^}]+)\}\}', card.front)
    if not match:
        return {
            'exercise_mode': 'cloze',
            'cloze_correct': '',
            'cloze_before': card.front,
            'cloze_after': '',
            'cloze_options': [],
        }

    correct = match.group(1).strip()
    before  = card.front[:match.start()]
    after   = card.front[match.end():]

    # gather distractor candidates
    candidates = []
    for c in Card.objects.filter(deck=card.deck, card_type='cloze').exclude(pk=card.pk)[:30]:
        candidates += re.findall(r'\{\{([^}]+)\}\}', c.front)
    for c in Card.objects.filter(deck=card.deck).exclude(pk=card.pk)[:40]:
        if c.back and len(c.back.strip()) <= 30:
            candidates.append(c.back.strip())

    seen = {correct.lower()}
    unique = []
    for w in candidates:
        w = w.strip()
        if w and w.lower() not in seen:
            seen.add(w.lower())
            unique.append(w)

    random.shuffle(unique)
    distractors = unique[:3]

    fillers = ['era', 'tiene', 'está', 'hace', 'van', 'son', 'fue', 'hay',
               'under', 'over', 'runs', 'eats']
    for f in fillers:
        if len(distractors) >= 3:
            break
        if f.lower() not in seen:
            distractors.append(f)
            seen.add(f.lower())

    options = [correct] + distractors[:3]
    random.shuffle(options)

    return {
        'exercise_mode': 'cloze',
        'cloze_correct': correct,
        'cloze_before': before,
        'cloze_after': after,
        'cloze_options': options,
    }


def _build_reveal_context(card, active_phase=False):
    """
    Build context for reveal-and-rate exercises.

    - translation cards (fase passiva): mostra back (PT), revela front (EN).
    - fase ativa (qualquer tipo): mesmo comportamento — produção PT→EN.
    - normal cards (fase passiva): mostra front (EN), revela back (PT).
    """
    if active_phase or card.card_type == Card.CARD_TYPE_TRANSLATION:
        return {
            'exercise_mode': 'reveal',
            'prompt_text':   card.back,
            'prompt_label':  'Traduza para o inglês:',
            'answer_text':   card.front,
            'answer_label':  'Resposta em inglês',
            'context_text':  card.context_sentence,
        }
    # normal card, fase passiva
    return {
        'exercise_mode': 'reveal',
        'prompt_text':   card.front,
        'prompt_label':  'Qual a tradução / resposta?',
        'answer_text':   card.back,
        'answer_label':  'Resposta',
        'context_text':  card.context_sentence,
    }


def _session_keys(lesson_id):
    base = f'trail_lesson_{lesson_id}'
    return {
        'queue':   f'{base}_queue',
        'total':   f'{base}_total',
        'done':    f'{base}_done',
        'correct': f'{base}_correct',
        'results': f'{base}_results',
    }


# ── Trail list ────────────────────────────────────────────────────────────────

@login_required
def trail_list(request):
    trails = Trail.objects.filter(user=request.user).prefetch_related('lessons')
    trail_data = []
    for trail in trails:
        total     = trail.total_lessons
        completed = trail.completed_count(request.user)
        trail_data.append({
            'trail':     trail,
            'total':     total,
            'completed': completed,
            'pct':       int(completed / total * 100) if total else 0,
        })

    # decks that have at least one cloze card and no trail yet
    deck_ids_with_trail = Trail.objects.filter(
        user=request.user, deck__isnull=False
    ).values_list('deck_id', flat=True)

    available_decks = [
        d for d in Deck.objects.filter(user=request.user)
        if d.cards.filter(card_type='cloze').exists()
        and d.pk not in deck_ids_with_trail
    ]

    return render(request, 'trails/list.html', {
        'trail_data':      trail_data,
        'available_decks': available_decks,
    })


# ── Trail create ──────────────────────────────────────────────────────────────

@login_required
@require_POST
def trail_create(request):
    deck_id = request.POST.get('deck_id')
    deck    = get_object_or_404(Deck, pk=deck_id, user=request.user)

    cloze_cards = list(deck.cards.filter(card_type='cloze'))
    if not cloze_cards:
        messages.error(request, 'Este deck não tem cards de cloze.')
        return redirect('trail_list')

    random.shuffle(cloze_cards)

    trail = Trail.objects.create(
        user=request.user,
        name=deck.name,
        description=deck.description or '',
        deck=deck,
        icon='📚',
    )

    chunks = [cloze_cards[i:i + LESSON_SIZE] for i in range(0, len(cloze_cards), LESSON_SIZE)]
    for idx, chunk in enumerate(chunks, start=1):
        title  = LESSON_TITLES[idx - 1] if idx <= len(LESSON_TITLES) else f'Lição {idx}'
        phase  = Lesson.PHASE_ACTIVE if idx > ACTIVE_PHASE_FROM else Lesson.PHASE_PASSIVE
        lesson = Lesson.objects.create(
            trail=trail,
            order=idx,
            title=title,
            xp_reward=10 * idx,
            phase=phase,
        )
        lesson.cards.set(chunk)

    messages.success(request, f'Trilha "{trail.name}" criada com {len(chunks)} lições!')
    return redirect('trail_detail', trail_id=trail.pk)


# ── Trail detail (visual path) ────────────────────────────────────────────────

@login_required
def trail_detail(request, trail_id):
    trail   = get_object_or_404(Trail, pk=trail_id, user=request.user)
    lessons = trail.lessons.prefetch_related('cards').all()

    lesson_data = []
    for lesson in lessons:
        lesson_data.append({
            'lesson':       lesson,
            'is_completed': lesson.is_completed(request.user),
            'is_unlocked':  lesson.is_unlocked(request.user),
            'card_count':   lesson.cards.count(),
        })

    total     = trail.total_lessons
    completed = trail.completed_count(request.user)

    return render(request, 'trails/detail.html', {
        'trail':       trail,
        'lesson_data': lesson_data,
        'total':       total,
        'completed':   completed,
        'pct':         int(completed / total * 100) if total else 0,
    })


# ── Lesson session ────────────────────────────────────────────────────────────

@login_required
def lesson_session(request, trail_id, lesson_id):
    trail  = get_object_or_404(Trail, pk=trail_id, user=request.user)
    lesson = get_object_or_404(Lesson, pk=lesson_id, trail=trail)

    if not lesson.is_unlocked(request.user):
        messages.warning(request, 'Complete a lição anterior primeiro.')
        return redirect('trail_detail', trail_id=trail_id)

    keys      = _session_keys(lesson_id)
    queue_ids = request.session.get(keys['queue'])

    if queue_ids is None:
        cards     = list(lesson.cards.all())
        random.shuffle(cards)
        queue_ids = [c.id for c in cards]
        request.session[keys['queue']]   = queue_ids
        request.session[keys['total']]   = len(queue_ids)
        request.session[keys['done']]    = 0
        request.session[keys['correct']] = 0
        request.session[keys['results']] = []  # [{front, back, correct}]

    if not queue_ids:
        return redirect('lesson_complete', trail_id=trail_id, lesson_id=lesson_id)

    card  = get_object_or_404(Card, id=queue_ids[0])
    total = request.session.get(keys['total'], len(queue_ids))
    done  = request.session.get(keys['done'], 0)

    is_active = (lesson.phase == Lesson.PHASE_ACTIVE)
    context = {
        'trail':        trail,
        'lesson':       lesson,
        'card':         card,
        'done':         done,
        'total':        total,
        'remaining':    len(queue_ids),
        'progress_pct': int(done / total * 100) if total else 0,
        'is_active':    is_active,
    }
    if card.card_type == Card.CARD_TYPE_CLOZE and not is_active:
        context.update(_build_cloze_context(card))
    else:
        context.update(_build_reveal_context(card, active_phase=is_active))
    return render(request, 'trails/session.html', context)


# ── Lesson answer (HTMX) ─────────────────────────────────────────────────────

@login_required
@require_POST
def lesson_answer(request, trail_id, lesson_id):
    trail  = get_object_or_404(Trail, pk=trail_id, user=request.user)
    lesson = get_object_or_404(Lesson, pk=lesson_id, trail=trail)

    card_id = request.POST.get('card_id')
    try:
        rating = int(request.POST.get('rating', 2))
    except (ValueError, TypeError):
        rating = 2

    keys      = _session_keys(lesson_id)
    queue_ids = list(request.session.get(keys['queue'], []))
    card      = get_object_or_404(Card, id=card_id)
    card_id_int = int(card_id)
    if card_id_int in queue_ids:
        queue_ids.remove(card_id_int)

    done      = request.session.get(keys['done'], 0) + 1
    is_correct = rating >= 2
    if is_correct:
        request.session[keys['correct']] = request.session.get(keys['correct'], 0) + 1

    # store per-card result for summary screen
    results = list(request.session.get(keys['results'], []))
    results.append({'front': card.front, 'back': card.back, 'correct': is_correct})
    request.session[keys['results']] = results

    request.session[keys['queue']] = queue_ids
    request.session[keys['done']]  = done
    request.session.modified = True

    if not queue_ids:
        url = reverse('lesson_complete', kwargs={'trail_id': trail_id, 'lesson_id': lesson_id})
        if request.htmx:
            return HttpResponseClientRedirect(url)
        return redirect(url)

    next_card = get_object_or_404(Card, id=queue_ids[0])
    total     = request.session.get(keys['total'], done)
    is_active = (lesson.phase == Lesson.PHASE_ACTIVE)

    context = {
        'trail':        trail,
        'lesson':       lesson,
        'card':         next_card,
        'done':         done,
        'total':        total,
        'remaining':    len(queue_ids),
        'progress_pct': int(done / total * 100) if total else 0,
        'is_active':    is_active,
    }
    if next_card.card_type == Card.CARD_TYPE_CLOZE and not is_active:
        context.update(_build_cloze_context(next_card))
    else:
        context.update(_build_reveal_context(next_card, active_phase=is_active))
    return render(request, 'trails/partials/exercise.html', context)


# ── Lesson complete ───────────────────────────────────────────────────────────

@login_required
def lesson_complete(request, trail_id, lesson_id):
    trail  = get_object_or_404(Trail, pk=trail_id, user=request.user)
    lesson = get_object_or_404(Lesson, pk=lesson_id, trail=trail)

    keys    = _session_keys(lesson_id)
    total   = request.session.get(keys['total'], 0)
    done    = request.session.get(keys['done'], 0)
    correct = request.session.get(keys['correct'], 0)
    results = list(request.session.get(keys['results'], []))
    accuracy = int(correct / done * 100) if done else 0

    for k in keys.values():
        request.session.pop(k, None)

    progress, _ = LessonProgress.objects.get_or_create(
        user=request.user, lesson=lesson
    )
    if not progress.completed or accuracy > progress.score:
        progress.completed    = True
        progress.score        = accuracy
        progress.xp_earned    = lesson.xp_reward
        progress.completed_at = timezone.now()
        progress.save()

    # ── Atualizar streak da trilha ────────────────────────────────────────
    today = date.today()
    trail_obj = Trail.objects.get(pk=trail.pk)
    if trail_obj.last_lesson_date == today:
        pass  # já estudou hoje, mantém streak
    elif trail_obj.last_lesson_date == today - timedelta(days=1):
        trail_obj.streak += 1
        trail_obj.last_lesson_date = today
        trail_obj.save()
    else:
        trail_obj.streak = 1
        trail_obj.last_lesson_date = today
        trail_obj.save()

    next_lesson = Lesson.objects.filter(
        trail=trail, order=lesson.order + 1
    ).first()

    return render(request, 'trails/complete.html', {
        'trail':       trail_obj,
        'lesson':      lesson,
        'total':       done,
        'correct':     correct,
        'wrong':       done - correct,
        'accuracy':    accuracy,
        'xp':          lesson.xp_reward,
        'next_lesson': next_lesson,
        'results':     results,
    })
