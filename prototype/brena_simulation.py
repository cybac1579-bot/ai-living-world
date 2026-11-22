"""Deterministic, offline Brena simulation core (not yet wired to Android UI).

No wall-clock access: time changes only through advance_time().
All character choices are simulation choices; player actions are never generated.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import json
import random

ACTIVITIES = (
    "help_villagers",
    "spear_training",
    "chief_house_life",
    "socializing",
    "personal_rest",
)
PLACES = ("square", "general_store", "inn", "smithy", "chief_house", "guard_training_ground")
ACTIVITY_PLACES = {
    "help_villagers": ("square", "general_store"),
    "spear_training": ("guard_training_ground",),
    "chief_house_life": ("chief_house",),
    "socializing": ("square", "inn"),
    "personal_rest": ("chief_house",),
}
MINUTES_PER_DAY = 1440


@dataclass
class Resident:
    key: str
    role: str
    place: str
    activity: str = "idle"
    memories: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return vars(self).copy()


@dataclass
class BrenaWorld:
    """State transitions are explicit; a new instance or save/load never advances time."""

    minute: int = 8 * 60
    day: int = 1
    seed: int = 1
    residents: dict[str, Resident] = field(default_factory=dict)
    relations: dict[str, dict[str, Any]] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    tick_index: int = 0

    @classmethod
    def new(cls, seed: int = 1) -> "BrenaWorld":
        world = cls(seed=seed)
        world.residents = {
            "rana": Resident("rana", "major", "chief_house"),
            "chief": Resident("chief", "major", "chief_house"),
            "smith": Resident("smith", "facility", "smithy"),
            "shopkeeper": Resident("shopkeeper", "facility", "general_store"),
            "innkeeper": Resident("innkeeper", "facility", "inn"),
            "resident_a": Resident("resident_a", "background", "square"),
            "resident_b": Resident("resident_b", "background", "square"),
        }
        return world

    def advance_time(self, minutes: int, *, rainy: bool = False, request_pending: bool = False) -> None:
        """Advance simulation time by a positive integer; each 60-minute boundary updates NPCs.

        Calling no method means no progression, including while the app is closed.
        """
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < 0:
            raise ValueError("minutes must be a nonnegative integer")
        if minutes > 365 * MINUTES_PER_DAY:
            raise ValueError("advance in chunks of at most one year")
        target = (self.day - 1) * MINUTES_PER_DAY + self.minute + minutes
        current = (self.day - 1) * MINUTES_PER_DAY + self.minute
        while current < target:
            boundary = (current // 60 + 1) * 60
            current = min(boundary, target)
            if current == boundary:
                self.tick_index += 1
                self._npc_tick(clock_hour=(current // 60) % 24, rainy=rainy, request_pending=request_pending)
        self.day = target // MINUTES_PER_DAY + 1
        self.minute = target % MINUTES_PER_DAY

    def _npc_tick(self, *, clock_hour: int, rainy: bool, request_pending: bool) -> None:
        rng = random.Random(f"{self.seed}:{self.tick_index}")
        rana = self.residents["rana"]
        # Sleep is based on the actual simulation hour, not elapsed tick count.
        if clock_hour in (0, 1, 2, 3, 4, 5):
            activity = "personal_rest"
        else:
            weights = [3, 3, 2, 2, 2]
            if rainy:
                weights[1] = 1
                weights[2] += 2
            if request_pending:
                weights[0] += 3
            activity = rng.choices(ACTIVITIES, weights=weights, k=1)[0]
        rana.activity = activity
        rana.place = rng.choice(ACTIVITY_PLACES[activity])
        for key, resident in self.residents.items():
            if key == "rana":
                continue
            if resident.role == "facility":
                # Minimal placeholder behavior, not a canon biography.
                resident.activity = "facility_duties"
            elif resident.role == "background":
                resident.activity = rng.choice(("daily_work", "socializing", "resting"))
                resident.place = rng.choice(("square", "chief_house", "inn"))
            else:
                resident.activity = "village_duties"

    def record_event(self, actor: str, subject: str, detail: str) -> None:
        if actor not in self.residents or subject not in self.residents:
            raise KeyError("event participants must exist")
        self.events.append({
            "day": self.day, "minute": self.minute,
            "actor": actor, "subject": subject, "detail": detail,
        })
        for key in {actor, subject}:
            self.residents[key].memories.append(detail)

    def set_relation(self, person_a: str, person_b: str, **state: Any) -> None:
        """Directional relation state. No single global spouse/partner slot."""
        if person_a == person_b:
            raise ValueError("relation requires two distinct persons")
        if not person_a or not person_b:
            raise ValueError("relation participants required")
        self.relations.setdefault(person_a, {}).setdefault(person_b, {}).update(state)

    def to_json(self) -> str:
        payload = {
            "version": 1, "minute": self.minute, "day": self.day,
            "seed": self.seed, "tick_index": self.tick_index,
            "residents": {k: v.as_dict() for k, v in self.residents.items()},
            "relations": self.relations, "events": self.events,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "BrenaWorld":
        raw = json.loads(text)
        if raw.get("version") != 1:
            raise ValueError("unsupported save version")
        world = cls(
            minute=raw["minute"], day=raw["day"],
            seed=raw["seed"], tick_index=raw["tick_index"],
        )
        if not 0 <= world.minute < MINUTES_PER_DAY or world.day < 1 or world.tick_index < 0:
            raise ValueError("invalid saved clock")
        world.residents = {k: Resident(**v) for k, v in raw["residents"].items()}
        world.relations = raw["relations"]
        world.events = raw["events"]
        return world
