from logging import Formatter


class ExtraFormatter(Formatter):

    def format(self, record):
        string = super().format(record)
        extra = {k: v for k, v in record.__dict__.items()}
        if len(extra) > 0:
            string += " - extra: " + str(extra)
        return string
