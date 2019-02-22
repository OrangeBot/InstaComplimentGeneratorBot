from datetime import datetime, timedelta
import time
import random, bisect
from copy import deepcopy

now = datetime.now  # wow this is bullshit
from pyutils import load_json

REQUEST_MEMORY_TIMEOUT = 300
CONTEMPLATION_TIMEOUT = 10

plural_map = {
    "eyes": True,
}


def is_plural(word):
    if word in plural_map:
        return plural_map[word]
    return word.endswith('s')


def get_plural_attrs(is_plural=False):
    return {
        "is": "are" if is_plural else "is",
        "this": "these" if is_plural else "this",
    }


def fill_n(message):
    parts = message.split('(n)')
    res = []
    for i, p in enumerate(parts[:-1]):
        res.append(p + ('n' if parts[i + 1].strip()[0].lower() in 'aeiou' else ''))
    res.append(parts[-1])
    return ''.join(res)


content = load_json('./content.json')
templates = load_json('./templates.json')


class WeightedRandomGenerator(object):
    def __init__(self, source):
        if isinstance(source, (list, tuple)):
            source = {s: 1 for s in source}
        self.totals = []
        running_total = 0
        self.results = []
        for k, v in source.items():
            self.results.append(k)
            running_total += v
            self.totals.append(running_total)

    def get_random_item(self):
        rnd = random.random() * self.totals[-1]
        return self.results[bisect.bisect_right(self.totals, rnd)]


class InstaComplimentBot(object):
    commands = ["exit", "random"]

    def __init__(self, mode='console'):
        self.last_request_ts = now() - timedelta(seconds=REQUEST_MEMORY_TIMEOUT)
        self.last_args = dict()
        self.mode = mode
        self.templates = WeightedRandomGenerator(templates)
        self.content_generators = {key: WeightedRandomGenerator(content[key]) for key in content}
        self._run_flag = True

    def on_message(self, text):
        if text.split()[0].lower() in self.commands:
            self.execute_command(*text.split())
        if text.isdigit():  # generate n compliments
            n = int(text)
            n = min(n, 50)
            self.random(n)

    def execute_command(self, command, *args):
        # self.last_args = args
        getattr(self, command.lower())(*args)

    def random(self, count=3):
        for _ in range(count):
            if now() - self.last_request_ts > timedelta(seconds=REQUEST_MEMORY_TIMEOUT):
                self.generate_compliment()
            else:
                self.generate_compliment(**self.last_args)

    def generate_compliment(self, template=None, wow=None, subj=None, adj=None, emo=None, **kwargs):
        template = template or self.templates.get_random_item()
        args = dict(
            subj=subj,
            wow=wow,
            adj=adj,
            emo=emo,
        )
        self.last_args = deepcopy(args)
        self.last_request_ts = now()
        for k in args:
            if args[k] is None:
                args[k] = self.content_generators[k].get_random_item()
        args.update(get_plural_attrs(is_plural(args['subj'])))

        self.send_message(template.format(**args))

    def exit(self):
        self._run_flag = False

    def run(self):
        self._run_flag = True
        while self._run_flag:
            message = self.get_message()
            self.on_message(message)
            self._run_flag and time.sleep(CONTEMPLATION_TIMEOUT)

    def get_message(self):
        if self.mode == "console":
            return raw_input("Next command:")
        else:
            raise NotImplementedError

    def send_message(self, message):
        message = fill_n(message).strip()
        if self.mode == "console":
            print(message[0].title() + message[1:])


if __name__ == '__main__':
    bot = InstaComplimentBot(mode='console')
    bot.run()
    # InstaComplimentBot.run()
