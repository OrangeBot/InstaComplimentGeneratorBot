from datetime import datetime, timedelta
import time
import random, bisect
from copy import deepcopy
from pyutils import trim

now = datetime.now  # wow this is bullshit
from pyutils import load_json
import telegram
import logging

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
LOG.addHandler(logging.StreamHandler())

REQUEST_MEMORY_TIMEOUT = 300
CONTEMPLATION_TIMEOUT = 10

plural_map = {
    "eyes": True,
    "this": False,
    "these": True,
    "dress": False,
}

from pyutils import format_to_text


def is_plural(word):
    if word in plural_map:
        return plural_map[word]
    return word.endswith('s')


def get_plural_attrs(is_plural=False):
    return {
        "is": "are" if is_plural else "is",
        # "this": "these" if is_plural else "this",
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
    commands = ["exit", "random", 'hello']

    def __init__(self, mode='console'):
        self.last_request_ts = now() - timedelta(seconds=REQUEST_MEMORY_TIMEOUT)
        self.last_args = dict()
        self.mode = mode
        self.templates = WeightedRandomGenerator(templates)
        self.content_generators = {key: WeightedRandomGenerator(content[key]) for key in content}
        self._run_flag = True

        self.greetings = WeightedRandomGenerator(load_json('./greetings.json'))

        if self.mode == "telegram":
            from pyutils import get_token  # done
            self.bot = telegram.Bot(get_token('./api.token'))
            self.update_id = None


    def execute_command(self, command, user=None, *args):
        # self.last_args = args
        getattr(self, command.lower())(*args)

    def random(self, count=3, user=None):
        for _ in range(count):
            # if now() - self.last_request_ts > timedelta(seconds=REQUEST_MEMORY_TIMEOUT):
            self.generate_compliment(user=user)
        # else:
        #     self.generate_compliment(user=user, **self.last_args)

    def generate_compliment(self, template=None, wow=None, subj=None, adj=None,verb=None, adjadj=None,
                            emo=None,
                            emo2=None,
                            emo3=None,
                            user=None,
                            **kwargs):
        template = template or self.templates.get_random_item()
        args = dict(
            subj=subj,
            wow=wow,
            adj=adj,
            emo=emo,
            emo2=emo2,
            emo3=emo3,
            verb=verb,
            adjadj=adjadj,
        )
        # self.last_args = deepcopy(args)
        # self.last_request_ts = now()
        for k in args:
            if args[k] is None:
                args[k] = self.content_generators[k].get_random_item()
        args.update(get_plural_attrs(is_plural(args['subj'])))
        compliment = template.format(**args)
        compliment = compliment.format(this=self.content_generators["this"].get_random_item())
        self.send_message(compliment, user=user)

    def exit(self):
        # self._run_flag = False
        pass

    def hello(self):
        self.send_message(self.greetings.get_random_item())

    def run(self):
        self._run_flag = True
        while self._run_flag:
            message, user = self.get_message()
            self.on_message(message, user=user)
            self.update_id += 1
            self._run_flag and time.sleep(CONTEMPLATION_TIMEOUT)

    def get_message(self):
        if self.mode == "console":
            return raw_input("Next command:"), None
        elif self.mode == "telegram":
            while True:
                try:
                    for update in self.bot.get_updates(offset=self.update_id, timeout=10):
                        self.update_id = update.update_id
                        if update.message:  # your bot can receive updates without messages
                            message = update.message.text
                            user = update.effective_user.id
                            LOG.info("Received message {} from user {}".format(message, user))
                            return message, user
                        self.update_id = update.update_id + 1
                except telegram.error.TimedOut:
                    pass
        else:
            raise NotImplementedError

    def send_message(self, message, user=None):
        message = fill_n(message).strip()
        if message.endswith('[no_this]'):
            message = trim(message, e='[no_this]').replace('this', '').replace('your', '')
        message = " ".join([p for p in message.split()]).replace(' ,', ',')
        message = message[0].title() + message[1:]
        if self.mode == "console":
            print(message)
        elif self.mode == "telegram":
            #     while True:
            #         try:
            #             for update in self.bot.get_updates(offset=self.update_id, timeout=10):
            #                 # Reply to the message
            #                 # update.message.reply_text(message)
            LOG.info('ending message "{}"'.format(format_to_text(message)))
            self.bot.send_message(chat_id=user, text=message)
        #         return None
        # except telegram.error.TimedOut:
        #     pass
        else:
            raise NotImplementedError

    def on_message(self, text, user):
        if text.split()[0].lower() in self.commands:
            self.execute_command(*text.split(), user=user)
        elif text.isdigit():  # generate n compliments
            n = int(text)
            n = min(n, 50)
            self.random(n, user=user)
        else:
            count = 1
            if text.split()[-1].isdigit():
                text, count = text.rsplit(None, 1)
                count = int(count)
            for _ in range(count):
                self.generate_compliment(subj="{this} " + text.lower(), user=user)
    # def connect_and_launch_telegram(self):
    #
    #
    #
    #     def message_handler(bot, update)
    #
    #     updater.dispatcher.add_handler(MessageHandler( hello))  # todo
    #
    #     def hello(bot, update): # todo
    #         message = 'Hello {}'.format(update.message.from_user.first_name)
    #         update.message.reply_text()
    #
    #     updater.dispatcher.add_handler(CommandHandler('hello', hello)) # todo
    #     from telegram.ext.
    #
    #     updater.start_polling()
    #     updater.idle()


if __name__ == '__main__':
    bot = InstaComplimentBot(mode='telegram')
    bot.run()
    # InstaComplimentBot.run()
