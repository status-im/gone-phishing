from __future__ import print_function
from rtmbot.core import Plugin

# TODO make zeromq forwarder, have all bots communicating
# http://zguide.zeromq.org/py:dechat
# https://learning-0mq-with-pyzmq.readthedocs.io/en/latest/pyzmq/devices/forwarder.html

class EarlyWarning(Plugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        print(self.__class__.__name__, 'initialized')

    def process_message(self, data):
        print(data)
        # Private (Groups) or Public Channels
        if chan.startswith('C') or chan.startswith('G'):
            chan = data['channel']
            text = data['text']

            # TODO paste into moderation channel

            if text.startswith(self.plugin_config.TRIGGER):
                user_ids = [line.strip()[:-1] for line in text.split('<@') if line.strip().endswith('>')]
                urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)

                # TODO Lookup user_id information, pass user_ids and urls into message queue, along with slack found in, and message text?