import re
import random

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django_htmx.http import HttpResponseClientRedirect
from django.urls import reverse

from .engine import get_daily_queue, process_review
from .models import ReviewLog
from decks.models import Card


def _build_cloze_context(card):
    """Return extra context vars needed to render a cloze multiple-choice card."""
    match = re.search(r'\{\{([^}]+)\}\}', card.front)
    if not match:
        return {}

    correct = match.group(1)
    before  = card.front[:match.start()]
    after   = card.front[match.end():]

    # ── gather distractor candidates ─────────────────────────────────────────
    candidates = []

    # words from other cloze cards in same deck
    for c in Card.objects.filter(deck=card.deck, card_type='cloze').exclude(pk=card.pk)[:30]:
        candidates += re.findall(r'\{\{([^}]+)\}\}', c.front)

    # short backs from any card in same deck
    for c in Card.objects.filter(deck=card.deck).exclude(pk=card.pk)[:40]:
        if c.back and len(c.back.strip()) <= 30:
            candidates.append(c.back.strip())

    # de-duplicate, remove correct answer
    seen = {correct.lower()}
    unique = []
    for w in candidates:
        w = w.strip()
        if w and w.lower() not in seen:
            seen.add(w.lower())
            unique.append(w)

    random.shuffle(unique)
    distractors = unique[:3]

    # pad with generic fillers if the deck is small
    fillers = ['era', 'tiene', 'está', 'hace', 'van', 'son', 'fue', 'hay']
    for f in fillers:
        if len(distractors) >= 3:
            break
        if f.lower() not in seen:
            distractors.append(f)
            seen.add(f.lower())

    options = [correct] + distractors[:3]
    random.shuffle(options)

    return {
        'cloze_correct': correct,
        'cloze_before':  before,
        'cloze_after':   after,
        'cloze_options': options,
    }


@login_required
def study_home(request):
    """Pre-session screen with today's queue summary."""
    queue = get_daily_queue(request.user)
    # Clear active session but preserve last_ids so "Estudar Novamente" still works
    for key in ('study_queue', 'study_total', 'study_done', 'study_correct'):
        request.session.pop(key, None)
    has_last = bool(request.session.get('study_last_ids'))
    return render(request, 'study/home.html', {
        'queue_count': len(queue),
        'has_last': has_last,
    })


@login_required
def study_session(request):
    """Main study session – shows current card."""
    queue_ids = request.session.get('study_queue')

    if queue_ids is None:
        # First visit: generate queue
        queue = get_daily_queue(request.user)
        queue_ids = [c.id for c in queue]
        # Save a copy so we can offer "Estudar Novamente" later
        request.session['study_last_ids'] = queue_ids.copy()
        request.session['study_queue'] = queue_ids
        request.session['study_total'] = len(queue_ids)
        request.session['study_done'] = 0
        request.session['study_correct'] = 0

    if not queue_ids:
        return redirect('study_complete')

    card = get_object_or_404(Card, id=queue_ids[0], deck__user=request.user)
    total = request.session.get('study_total', len(queue_ids))
    done = request.session.get('study_done', 0)

    context = {
        'card': card,
        'done': done,
        'total': total,
        'remaining': len(queue_ids),
        'progress_pct': int(done / total * 100) if total > 0 else 0,
    }
    if card.card_type == 'cloze':
        context.update(_build_cloze_context(card))
    return render(request, 'study/session.html', context)


@login_required
@require_POST
def study_answer(request):
    """Process rating for a card and return the next card (HTMX)."""
    card_id = request.POST.get('card_id')
    try:
        rating = int(request.POST.get('rating', 2))
        time_spent_ms = request.POST.get('time_spent_ms')
        time_spent_ms = int(time_spent_ms) if time_spent_ms else None
    except (ValueError, TypeError):
        rating = 2
        time_spent_ms = None

    card = get_object_or_404(Card, id=card_id, deck__user=request.user)
    process_review(card, rating, request.user, time_spent_ms)

    # Update session
    queue_ids = list(request.session.get('study_queue', []))
    card_id_int = int(card_id)
    if card_id_int in queue_ids:
        queue_ids.remove(card_id_int)

    done = request.session.get('study_done', 0) + 1
    if rating >= 2:
        request.session['study_correct'] = request.session.get('study_correct', 0) + 1

    request.session['study_queue'] = queue_ids
    request.session['study_done'] = done
    request.session.modified = True

    if not queue_ids:
        if request.htmx:
            return HttpResponseClientRedirect(reverse('study_complete'))
        return redirect('study_complete')

    next_card = get_object_or_404(Card, id=queue_ids[0], deck__user=request.user)
    total = request.session.get('study_total', done)

    context = {
        'card': next_card,
        'done': done,
        'total': total,
        'remaining': len(queue_ids),
        'progress_pct': int(done / total * 100) if total > 0 else 0,
    }
    if next_card.card_type == 'cloze':
        context.update(_build_cloze_context(next_card))
    return render(request, 'study/partials/card.html', context)


@login_required
def study_complete(request):
    """Session complete summary page."""
    total = request.session.get('study_total', 0)
    done = request.session.get('study_done', 0)
    correct = request.session.get('study_correct', 0)
    last_count = len(request.session.get('study_last_ids', []))

    for key in ('study_queue', 'study_total', 'study_done', 'study_correct'):
        request.session.pop(key, None)
    # study_last_ids is intentionally kept for "Estudar Novamente"

    accuracy = int(correct / done * 100) if done > 0 else 0

    return render(request, 'study/complete.html', {
        'total': done,
        'correct': correct,
        'accuracy': accuracy,
        'last_count': last_count,
    })


@login_required
def study_restart(request):
    """Restart session with the same cards reshuffled.
    Falls back to the daily queue if no previous session exists."""
    last_ids = list(request.session.get('study_last_ids', []))

    if last_ids:
        # Validate cards still belong to the user
        valid_ids = list(
            Card.objects.filter(id__in=last_ids, deck__user=request.user)
            .values_list('id', flat=True)
        )
    else:
        valid_ids = []

    if not valid_ids:
        # Fallback: generate a fresh daily queue shuffled
        queue = get_daily_queue(request.user)
        valid_ids = [c.id for c in queue]
        if not valid_ids:
            return redirect('study_home')

    random.shuffle(valid_ids)

    request.session['study_last_ids'] = valid_ids.copy()
    request.session['study_queue'] = valid_ids
    request.session['study_total'] = len(valid_ids)
    request.session['study_done'] = 0
    request.session['study_correct'] = 0

    return redirect('study_session')


# ── Gesture Flashcards ────────────────────────────────────────────────────────

@login_required
def gesture_session(request):
    """Gesture-mode study session (Easy/Hard only)."""
    queue_ids = request.session.get('gesture_queue')

    if queue_ids is None:
        queue = get_daily_queue(request.user)
        queue_ids = [c.id for c in queue]
        request.session['gesture_last_ids'] = queue_ids.copy()
        request.session['gesture_queue']    = queue_ids
        request.session['gesture_total']    = len(queue_ids)
        request.session['gesture_done']     = 0
        request.session['gesture_correct']  = 0

    if not queue_ids:
        return redirect('gesture_complete')

    card  = get_object_or_404(Card, id=queue_ids[0], deck__user=request.user)
    total = request.session.get('gesture_total', len(queue_ids))
    done  = request.session.get('gesture_done', 0)

    return render(request, 'study/gesture_session.html', {
        'card':         card,
        'done':         done,
        'total':        total,
        'remaining':    len(queue_ids),
        'progress_pct': int(done / total * 100) if total else 0,
    })


@login_required
@require_POST
def gesture_answer(request):
    """Process gesture-mode rating and return next card (HTMX)."""
    card_id = request.POST.get('card_id')
    try:
        rating = int(request.POST.get('rating', 2))
    except (ValueError, TypeError):
        rating = 2

    card = get_object_or_404(Card, id=card_id, deck__user=request.user)
    process_review(card, rating, request.user, None)

    queue_ids   = list(request.session.get('gesture_queue', []))
    card_id_int = int(card_id)
    if card_id_int in queue_ids:
        queue_ids.remove(card_id_int)

    done = request.session.get('gesture_done', 0) + 1
    if rating >= 2:
        request.session['gesture_correct'] = request.session.get('gesture_correct', 0) + 1

    request.session['gesture_queue'] = queue_ids
    request.session['gesture_done']  = done
    request.session.modified = True

    if not queue_ids:
        url = reverse('gesture_complete')
        if request.htmx:
            return HttpResponseClientRedirect(url)
        return redirect(url)

    next_card = get_object_or_404(Card, id=queue_ids[0], deck__user=request.user)
    total     = request.session.get('gesture_total', done)

    return render(request, 'study/partials/gesture_card.html', {
        'card':         next_card,
        'done':         done,
        'total':        total,
        'remaining':    len(queue_ids),
        'progress_pct': int(done / total * 100) if total else 0,
    })


@login_required
def gesture_complete(request):
    """Gesture session complete."""
    total   = request.session.get('gesture_total', 0)
    done    = request.session.get('gesture_done', 0)
    correct = request.session.get('gesture_correct', 0)
    for key in ('gesture_queue', 'gesture_total', 'gesture_done', 'gesture_correct'):
        request.session.pop(key, None)
    accuracy = int(correct / done * 100) if done else 0
    return render(request, 'study/complete.html', {
        'total': done, 'correct': correct, 'accuracy': accuracy, 'last_count': 0,
    })
