import random
from collections import deque
from itertools import product, chain


class Deck:
    """Creates a Deck of playing cards."""

    suites = (":clubs:", ":diamonds:", ":hearts:", ":spades:")
    face_cards = ("King", "Queen", "Jack", "Ace")
    bj_vals = {"Jack": 10, "Queen": 10, "King": 10, "Ace": 1}
    war_values = {"Jack": 11, "Queen": 12, "King": 13, "Ace": 14}

    def __init__(self):
        self._deck = deque()

    def __len__(self):
        return len(self._deck)

    def __str__(self):
        return "Standard deck of cards with {} cards remaining.".format(len(self._deck))

    def __repr__(self):
        return "Deck{!r}".format(self._deck)

    @property
    def deck(self):
        if len(self._deck) < 1:
            self.new()
        return self._deck

    def shuffle(self):
        random.shuffle(self._deck)

    def war_count(self, card):
        try:
            return self.war_values[card[1]]
        except KeyError:
            return card[1]

    def bj_count(self, hand: list, hole=False):
        hand = self._hand_type(hand)
        if hole:
            card = hand[0][1]
            count = self.bj_vals[card] if isinstance(card, str) else card
            return count if count > 1 else 11

        count = sum([self.bj_vals[y] if isinstance(y, str) else y for x, y in hand])
        if any("Ace" in pair for pair in hand) and count <= 11:
            count += 10
        return count

    @staticmethod
    def fmt_hand(hand: list):
        return ["{} {}".format(y, x) for x, y in hand]

    @staticmethod
    def fmt_card(card):
        return "{1} {0}".format(*card)

    @staticmethod
    def hand_check(hand: list, card):
        return any(x[1] == card for x in hand)

    def split(self, position: int):
        self._deck.rotate(-position)

    @staticmethod
    def _true_hand(hand: list):
        return [x.split(" ") for x in hand]

    def draw(self, top=True):
        self._check()

        if top:
            card = self._deck.popleft()
        else:
            card = self._deck.pop()
        return card

    def _check(self, num=1):
        if num > 52:
            raise ValueError("Can not exceed deck limit.")
        if len(self._deck) < num:
            self.new()

    def _hand_type(self, hand: list):
        if isinstance(hand[0], tuple):
            return hand

        try:
            return self._true_hand(hand)
        except ValueError:
            raise ValueError("Invalid hand input.")

    def deal(self, num=1, top=True, hand=None):
        self._check(num=num)

        if hand is None:
            hand = []
        for x in range(0, num):
            if top:
                hand.append(self._deck.popleft())
            else:
                hand.append(self._deck.pop())

        return hand

    def burn(self, num):
        self._check(num=num)
        for x in range(0, num):
            del self._deck[0]

    def new(self):
        cards = product(self.suites, chain(range(2, 11), ("King", "Queen", "Jack", "Ace")))
        self._deck = deque(cards)
        self.shuffle()
