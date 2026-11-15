"""Probability operations for distribution-preserving speculative verification.

Inputs are normalized distributions after the configured temperature/top-p transform.
"""
import math
from itertools import chain, zip_longest


def normalize_top_p(logits, vocab_tokens, temperature, top_p):
    """Reference sampling policy shared by draft, target and target-only baselines."""
    if (not 0 < vocab_tokens <= len(logits) or not temperature > 0 or
            not 0 < top_p <= 1):
        raise ValueError("Invalid vocabulary size, temperature or top-p")
    active = logits[:vocab_tokens]
    if any(math.isnan(x) or x == math.inf for x in active):
        raise ValueError("Logits contain NaN or positive infinity")
    peak = max(active)
    if peak == -math.inf:
        raise ValueError("All active logits are masked")
    weights = [math.exp((x - peak) / temperature) for x in active]
    total = math.fsum(weights)
    probabilities = [weight / total for weight in weights]
    if top_p == 1:
        return probabilities
    order = sorted(range(vocab_tokens), key=lambda token: (-probabilities[token], token))
    retained = [0.0] * vocab_tokens
    mass = 0.0
    for token in order:
        retained[token] = probabilities[token]
        mass += probabilities[token]
        if mass >= top_p:
            break
    return [probability / mass for probability in retained]


def accept_probability(target_probability, draft_probability):
    if not 0 <= target_probability <= 1 or not 0 < draft_probability <= 1:
        raise ValueError("Expected target probability in [0, 1] and positive draft probability")
    return min(1.0, target_probability / draft_probability)


def residual_distribution(target, draft):
    if not target or not draft:
        raise ValueError("Target and draft distributions must be nonempty")
    if (any(not math.isfinite(x) or x < 0 for x in chain(target, draft)) or
            abs(math.fsum(target) - 1) > 1e-6 or abs(math.fsum(draft) - 1) > 1e-6):
        raise ValueError("Target and draft must be normalized probability distributions")
    difference = [max(p - q, 0.0) for p, q in zip_longest(target, draft, fillvalue=0.0)]
    mass = math.fsum(difference)
    return [x / mass for x in difference] if mass > 0 else list(target) + [0.0] * max(0, len(draft) - len(target))


def _draw(probabilities, rng):
    total = math.fsum(probabilities)
    if total <= 0:
        raise ValueError("Cannot sample from zero probability mass")
    draw = rng.random() * total
    cumulative = 0.0
    last_positive = None
    for token, probability in enumerate(probabilities):
        if probability > 0:
            last_positive = token
        cumulative += probability
        if draw < cumulative:
            return token
    return last_positive  # Floating-point summation can leave a tiny gap.


def verify_round(proposals, draft_distributions, target_distributions, rng):
    """Verify one speculative round; target_distributions includes the bonus position."""
    if (not proposals or len(proposals) != len(draft_distributions) or
            len(target_distributions) != len(proposals) + 1):
        raise ValueError("Expected K proposals, K draft distributions and K+1 target distributions")
    committed = []
    for index, token in enumerate(proposals):
        draft = draft_distributions[index]
        target = target_distributions[index]
        if not isinstance(token, int) or token < 0 or token >= len(draft):
            raise ValueError("Proposal token is outside the draft vocabulary")
        residual = residual_distribution(target, draft)
        target_probability = target[token] if token < len(target) else 0.0
        if rng.random() < accept_probability(target_probability, draft[token]):
            committed.append(token)
            continue
        committed.append(_draw(residual, rng))
        return {"tokens": committed, "accepted_draft_tokens": index, "rejected_at": index}
    bonus = target_distributions[-1]
    if not bonus or any(x < 0 or not math.isfinite(x) for x in bonus) or abs(math.fsum(bonus) - 1) > 1e-6:
        raise ValueError("Bonus target distribution must be normalized")
    committed.append(_draw(bonus, rng))
    return {"tokens": committed, "accepted_draft_tokens": len(proposals), "rejected_at": None}
