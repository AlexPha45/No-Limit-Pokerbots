"""Fast, fixed Boston policies. This module is copied into each upload artifact."""

import gc
import itertools
import json
import math
import struct
from pathlib import Path

import eval7
from poker_agent_sdk import Action, icm

_POLICY = json.loads(Path(__file__).with_name("policy.json").read_text())
_CLASSES = _POLICY["classes"]
_RANKS = "23456789TJQKA"
_RANK_VALUE = {rank: i + 2 for i, rank in enumerate(_RANKS)}
_WINDOWS = ((14, 2, 3, 4, 5), *(tuple(range(low, low + 5)) for low in range(2, 11)))
_MEMORY = struct.Struct("!2sHH")
# The decision path creates only acyclic temporary values; cyclic GC pauses are avoidable.
gc.disable()


def _class_name(cards):
    a, b = cards
    ra, rb = a[0], b[0]
    if _RANK_VALUE[ra] < _RANK_VALUE[rb]:
        ra, rb = rb, ra
    return ra + rb if ra == rb else ra + rb + ("s" if a[1] == b[1] else "o")


def _remember(state, memory):
    # Policies are fixed, so table memory is bookkeeping only. Bad/stale memory is ignored.
    try:
        magic, hand, seen = _MEMORY.unpack(memory)
        if magic != b"B1" or hand > state.hand_number:
            raise ValueError
        if hand == state.hand_number and seen > len(state.history):
            raise ValueError
    except (ValueError, TypeError, struct.error):
        pass
    return _MEMORY.pack(b"B1", min(65535, state.hand_number), min(65535, len(state.history)))


def _fallback(state):
    if state.can("check"):
        return Action.check()
    if state.can("fold"):
        return Action.fold()
    if state.can("bid"):
        return Action("bid", cards=(0, 0, 0, 0, 0))
    first = state.legal_actions[0]
    return Action(first.kind, first.min_amount)


def _legal(state, action):
    legal = state.can(action.kind)
    if legal is None or type(action.amount) is not int:
        return False
    if action.kind == "raise":
        return not action.cards and legal.min_amount <= action.amount <= legal.max_amount
    if action.kind == "bid":
        return (action.amount == 0 and len(action.cards) == 5
                and all(type(b) is int and b >= 0 for b in action.cards)
                and sum(action.cards) <= legal.max_amount)
    return action.amount == 0 and not action.cards


def _raise(state, target):
    legal = state.can("raise")
    if legal is None:
        return None
    return Action.raise_to(max(legal.min_amount, min(legal.max_amount, int(target))))


def _position(state):
    alive = [seat.seat for seat in state.seats if seat.status != "busted"]
    if state.seat == state.button:
        return "button"
    if state.button not in alive or state.seat not in alive:
        return "middle"
    start = alive.index(state.button)
    order = alive[start + 1:] + alive[:start]
    if state.seat == order[0]:
        return "small_blind"
    if len(order) > 1 and state.seat == order[1]:
        return "big_blind"
    if state.seat == order[-1]:
        return "cutoff"
    return "early" if order.index(state.seat) < max(3, len(order) - 3) else "middle"


def _open_fraction(state, mode):
    depth = (next((s.stack + s.bet for s in state.seats if s.seat == state.seat), 0)
             / max(1, state.blinds.big_blind))
    low = depth <= 12
    position = _position(state)
    # UTG/BTN anchors come from the cited public charts; other spots are interpolation.
    fractions = ({"early": .1685, "middle": .23, "cutoff": .32, "button": .389,
                  "small_blind": .42, "big_blind": .24} if low else
                 {"early": .102, "middle": .18, "cutoff": .29, "button": .408,
                  "small_blind": .34, "big_blind": .20})
    fraction = fractions[position]
    if mode == "LEVEL_2":
        fraction *= 1.17  # Fixed wider policy; never changed by an opponent's table history.
    return min(.6, fraction), depth


def _opponents(state):
    return sum(s.seat != state.seat and s.status in ("active", "all_in") for s in state.seats)


def _preflop_share(state, hand_class):
    all_in_share = _CLASSES[hand_class]["modeled_auction"]["auction_share"]
    contenders = max(2, min(8, 1 + sum(s.seat != state.seat and s.bet >= state.blinds.big_blind
                                       and s.status in ("active", "all_in") for s in state.seats)))
    return max(.02, min(.95, all_in_share ** (math.log(contenders) / math.log(8))))


def _postflop_share(state):
    cards = tuple(eval7.Card(card) for card in (*state.cards, *state.board))
    category = eval7.handtype(eval7.evaluate(cards))
    base = {"High Card": .18, "Pair": .43, "Two Pair": .70, "Trips": .82,
            "Straight": .88, "Flush": .91, "Full House": .97,
            "Quads": .995, "Straight Flush": .999}[category]
    if category == "Pair":
        ranks = [card[0] for card in (*state.cards, *state.board)]
        paired = next((r for r in ranks if ranks.count(r) >= 2), None)
        if paired not in (state.cards[0][0], state.cards[1][0]):
            base = .32
        elif paired is not None and _RANK_VALUE[paired] >= max(_RANK_VALUE[c[0]] for c in state.board):
            base = .55
    dead = set(state.variant.get("auction_cards", ())) - set(state.board)
    known = set((*state.cards, *state.board)) | dead
    unseen = max(1, 52 - len(known))
    outs = 0
    if len(state.board) < 5 and category not in ("Flush", "Straight Flush"):
        for suit in "cdhs":
            if sum(card[1] == suit for card in (*state.cards, *state.board)) == 4:
                outs = max(outs, 13 - sum(card[1] == suit for card in known))
    if len(state.board) < 5 and category not in ("Straight", "Straight Flush"):
        have = {_RANK_VALUE[c[0]] for c in (*state.cards, *state.board)}
        for window in _WINDOWS:
            missing = set(window) - have
            if len(missing) == 1:
                rank = next(iter(missing))
                outs = max(outs, 4 - sum(_RANK_VALUE[c[0]] == rank for c in known))
    if outs:
        draw_p = outs / unseen
        if len(state.board) == 3:
            draw_p = 1 - (1 - draw_p) * (1 - outs / max(1, unseen - 1))
        base = min(.95, base + .45 * draw_p)
    return max(.01, min(.999, base ** (1 + .23 * max(0, _opponents(state) - 1))))


def _call_utility(state, share, cost):
    if cost <= 0:
        return True
    stacks = [seat.stack for seat in state.seats]
    hero = state.seat
    villain = max((i for i, seat in enumerate(state.seats) if i != hero and seat.status in ("active", "all_in")),
                  key=lambda i: state.seats[i].bet, default=None)
    if villain is None or hero >= len(stacks) or cost > stacks[hero]:
        return False
    payouts = state.config.payouts
    # Full ICM is used at the bubble, for major stack risks, and near the hand cap.
    # A cheap payout-aware risk premium handles ordinary small calls inside 1 ms.
    paid = sum(value > 0 for value in payouts)
    remaining = state.players_remaining
    if remaining > max(4, paid + 1) and state.config.hand_cap - state.hand_number > 0:
        threshold = cost / max(1, state.pot + cost)
        payout_gap = payouts[paid - 1] - (payouts[paid] if paid < len(payouts) else 0)
        pressure = (1 + .08 * min(3, sum(stacks[hero] < stack for stack in stacks if stack > 0))
                    + max(0, payout_gap) / max(1, sum(payouts)) * cost / max(1, stacks[hero]))
        return share >= min(.95, threshold * pressure + .015)
    folded = stacks.copy(); folded[villain] += state.pot
    won = stacks.copy(); won[hero] += state.pot
    lost = stacks.copy(); lost[hero] -= cost; lost[villain] += state.pot + cost
    u_fold = icm(folded, payouts)[hero]
    u_win = icm(won, payouts)[hero]
    u_lose = icm(lost, payouts)[hero]
    return share * u_win + (1 - share) * u_lose > u_fold + 1e-7


def _betting(state, mode):
    preflop = len(state.board) == 0
    share = _preflop_share(state, _class_name(state.cards)) if preflop else _postflop_share(state)
    check = state.can("check")
    call = state.can("call")
    raise_ = state.can("raise")
    if preflop:
        cutoff, depth = _open_fraction(state, mode)
        percentile = _CLASSES[_class_name(state.cards)]["percentile"]
        raised = any(event.kind == "raise" for event in state.history)
        if not raised and raise_:
            # The big blind makes `call` legal even in an unopened pot. Handle the
            # open before the call branch or almost every playable hand limps.
            # Boston has no starting ante; use a conservative fraction of the
            # outside chart's opening ranges until round evidence supports more.
            open_limit = cutoff * .85
            if percentile <= open_limit:
                limpers = sum(event.kind == "call" and event.seat != state.seat
                              for event in state.history)
                target = (raise_.max_amount if depth <= 10 and percentile <= open_limit * .65
                          else math.ceil((2.5 + limpers) * state.blinds.big_blind))
                return _raise(state, max(raise_.min_amount, target))
            if check:
                return Action.check()
            return Action.fold() if state.can("fold") else Action.call()
        if check:
            if raise_ and percentile <= cutoff:
                target = (raise_.max_amount if depth <= 10 and percentile <= cutoff * .65
                          else max(raise_.min_amount, math.ceil(2.5 * state.blinds.big_blind)))
                return _raise(state, target)
            return Action.check()
        if call:
            eligible = percentile <= cutoff * (.55 if raised else .9)
            if eligible and _call_utility(state, share, min(state.to_call, state.seats[state.seat].stack)):
                if raise_ and percentile <= min(.055 if mode == "LEVEL_1" else .075, cutoff * .25):
                    return _raise(state, max(raise_.min_amount, 3 * max(s.bet for s in state.seats)))
                return Action.call()
            return Action.fold() if state.can("fold") else Action.call()
    else:
        if check:
            if raise_ and share >= (.70 if mode == "LEVEL_1" else .64):
                fraction = .5 if mode == "LEVEL_1" else .67
                return _raise(state, state.seats[state.seat].bet + max(state.blinds.big_blind, int(state.pot * fraction)))
            if mode == "LEVEL_2" and raise_ and share >= .38 and _opponents(state) == 1:
                return _raise(state, state.seats[state.seat].bet + max(state.blinds.big_blind, state.pot // 2))
            return Action.check()
        if call:
            cost = min(state.to_call, state.seats[state.seat].stack)
            if _call_utility(state, share, cost):
                if raise_ and share >= (.88 if mode == "LEVEL_1" else .80):
                    return _raise(state, max(raise_.min_amount, 3 * max(s.bet for s in state.seats)))
                return Action.call()
            return Action.fold() if state.can("fold") else Action.call()
    return _fallback(state)


def _auction_score(hole, flop):
    cards = tuple(eval7.Card(card) for card in (*hole, *flop))
    category = eval7.handtype(eval7.evaluate(cards))
    value = {"High Card": 0, "Pair": 1.0, "Two Pair": 2.2, "Trips": 3.1,
             "Straight": 4.2, "Flush": 5.0, "Full House": 6.0,
             "Quads": 7.0, "Straight Flush": 8.0}[category]
    ranks = {_RANK_VALUE[c[0]] for c in (*hole, *flop)}
    if category not in ("Straight", "Straight Flush"):
        value += .3 * any(len(ranks & set(window)) == 4 for window in _WINDOWS)
    if category not in ("Flush", "Straight Flush"):
        value += .35 * any(sum(c[1] == suit for c in (*hole, *flop)) == 4 for suit in "cdhs")
    return value


def _auction(state, mode):
    legal = state.can("bid")
    cards = state.variant.get("auction_cards", ())
    if legal is None or len(cards) != 5 or len(set(cards)) != 5 or len(state.cards) != 2:
        return Action("bid", cards=(0, 0, 0, 0, 0))
    balance = min(legal.max_amount, int(state.variant.get("flop_chips", legal.max_amount)))
    remaining = max(1, state.config.hand_cap - state.hand_number + 1)
    budget = min(balance, math.ceil(balance / max(1, .4 * remaining)))
    if mode == "LEVEL_2":
        budget = min(balance, math.ceil(1.4 * budget))
    if budget < 3:
        return Action("bid", cards=(0, 0, 0, 0, 0))
    default = _auction_score(state.cards, cards[:3])
    best, chosen = default, (0, 1, 2)
    for indexes in itertools.combinations(range(5), 3):
        score = _auction_score(state.cards, tuple(cards[i] for i in indexes))
        if score > best:
            best, chosen = score, indexes
    if best - default < (.30 if mode == "LEVEL_1" else .20):
        return Action("bid", cards=(0, 0, 0, 0, 0))
    amounts = [0] * 5
    for index in chosen:
        amounts[index] = budget // 3
    for index in chosen[:budget % 3]:
        amounts[index] += 1
    return Action("bid", cards=tuple(amounts))


def decide(state, memory, mode):
    remembered = _remember(state, memory)
    try:
        action = _auction(state, mode) if state.phase == "auction" else (
            _betting(state, mode) if state.phase == "betting" else _fallback(state))
        if action is None or not _legal(state, action):
            action = _fallback(state)
    except Exception:
        action = _fallback(state)
    return action, remembered
