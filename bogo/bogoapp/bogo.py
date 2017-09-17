import ast
from bogoapp import tools


class Bogo:
    """
    Encapsulates bogosorting state for a single sequence and is also a crappy ORM.
    Considered finished when its sequence is sorted.
    """
    def __init__(self,
                 db_id=None,
                 sequence=None,
                 created=None,
                 finished=None,
                 shuffles=0):
        self.db_id = db_id
        self.sequence = sequence
        self.created = created
        self.finished = finished
        self.shuffles = shuffles

    @classmethod
    def from_database_row(cls, row):
        sequence = ast.literal_eval(row[1])
        return cls(row[0], sequence, *row[2:])

    def as_database_row(self):
        return (self.db_id,
                repr(self.sequence),
                self.created,
                self.finished,
                self.shuffles)

    def shuffle_with(self, shuffle):
        shuffle(self.sequence)
        self.shuffles += 1

    def is_finished(self):
        return self.finished is not None or tools.is_sorted(self.sequence)

    def __repr__(self):
        return "<class 'Bogo' with sequence: {}>".format(repr(self.sequence))

