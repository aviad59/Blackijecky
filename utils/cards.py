# utils/cards.py
import random
from dataclasses import dataclass

# suit encoding: Heart, Diamond, Club, Spade => 0,1,2,3
SUITS = [0, 1, 2, 3]  # HDCS
RANKS = list(range(1, 14))  # 1..13 (A..K)


@dataclass(frozen=True)
class Card:
    rank: int  # 1..13
    suit: int  # 0..3


def card_value(rank: int) -> int:
    # A=11, J/Q/K=10, else rank
    if rank == 1:
        return 11
    if 11 <= rank <= 13:
        return 10
    return rank


class Deck:
    def __init__(self):
        self.cards = [Card(r, s) for s in SUITS for r in RANKS]
        random.shuffle(self.cards)

    def draw(self) -> Card:
        if not self.cards:
            # generete new if empty
            self.__init__()
        return self.cards.pop()
