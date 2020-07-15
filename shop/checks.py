from collections import Iterable


class Checks:
    """Class of predicates for waiting events.

    This class requires you to pass ctx so that the person who
    invocated the command can be determined.

    You may pass an optional iterable in custom to check if the
    content is a member of it.
    """

    def __init__(self, ctx, custom: Iterable = None, length: int = None):
        self.ctx = ctx
        self.custom = custom
        self.length = length

    def same(self, m):
        return self.ctx.author == m.author

    def confirm(self, m):
        return self.same(m) and m.content.lower() in ("yes", "no")

    def valid_int(self, m):
        return self.same(m) and m.content.isdigit()

    def valid_float(self, m):
        try:
            return self.same(m) and float(m.content) >= 1
        except ValueError:
            return False

    def positive(self, m):
        return self.same(m) and m.content.isdigit() and int(m.content) > 0

    def role(self, m):
        roles = [r.name for r in self.ctx.guild.roles if r.name != "Bot"]
        return self.same(m) and m.content in roles

    def member(self, m):
        return self.same(m) and m.content in [x.name for x in self.ctx.guild.members]

    def length_under(self, m):
        try:
            return self.same(m) and len(m.content) <= self.length
        except TypeError:
            raise ValueError("Length was not specified in Checks.")

    def content(self, m):
        try:
            return self.same(m) and m.content in self.custom
        except TypeError:
            raise ValueError("A custom iterable was not set in Checks.")
