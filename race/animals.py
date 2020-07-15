import random

racers = (
    (":rabbit2:", "fast"),
    (":monkey:", "fast"),
    (":cat2:", "fast"),
    (":mouse2:", "slow"),
    (":chipmunk:", "fast"),
    (":rat:", "fast"),
    (":dove:", "fast"),
    (":bird:", "fast"),
    (":dromedary_camel:", "steady"),
    (":camel:", "steady"),
    (":dog2:", "steady"),
    (":poodle:", "steady"),
    (":racehorse:", "steady"),
    (":ox:", "abberant"),
    (":cow2:", "abberant"),
    (":elephant:", "abberant"),
    (":water_buffalo:", "abberant"),
    (":ram:", "abberant"),
    (":goat:", "abberant"),
    (":sheep:", "abberant"),
    (":leopard:", "predator"),
    (":tiger2:", "predator"),
    (":dragon:", "special"),
    (":unicorn:", "special"),
    (":turtle:", "slow"),
    (":bug:", "slow"),
    (":rooster:", "slow"),
    (":snail:", "slow"),
    (":scorpion:", "slow"),
    (":crocodile:", "slow"),
    (":pig2:", "slow"),
    (":turkey:", "slow"),
    (":duck:", "slow"),
    (":baby_chick:", "slow"),
)


class Animal:
    def __init__(self, emoji, _type):
        self.emoji = emoji
        self._type = _type
        self.track = "•   " * 20
        self.position = 80
        self.turn = 0
        self.current = self.track + self.emoji

    def move(self):
        self._update_postion()
        self.turn += 1
        return self.current

    def _update_postion(self):
        distance = self._calculate_movement()
        self.current = "".join(
            (
                self.track[: max(0, self.position - distance)],
                self.emoji,
                self.track[max(0, self.position - distance) :],
            )
        )
        self.position = self._get_position()

    def _get_position(self):
        return self.current.find(self.emoji)

    def _calculate_movement(self):
        if self._type == "slow":
            return random.randint(1, 3) * 3
        elif self._type == "fast":
            return random.randint(0, 4) * 3

        elif self._type == "steady":
            return 2 * 3

        elif self._type == "abberant":
            if random.randint(1, 100) >= 90:
                return 5 * 3
            else:
                return random.randint(0, 2) * 3

        elif self._type == "predator":
            if self.turn % 2 == 0:
                return 0
            else:
                return random.randint(2, 5) * 3

        elif self._type == ":unicorn:":
            if self.turn % 3:
                return random.choice([len("blue"), len("red"), len("green")]) * 3
            else:
                return 0
        else:
            if self.turn == 1:
                return 14 * 3
            elif self.turn == 2:
                return 0
            else:
                return random.randint(0, 2) * 3
