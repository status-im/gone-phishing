from __future__ import print_function
from rtmbot.core import Plugin


class ChannelJoiner(Plugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        r = self.slack.channels.list(exclude_archived=True)
        channels = r.body['channels']

        # TODO Requires Invitation: groups.invite
        # r = slack.groups.list(exclude_archived=True)
        # groups = r.body['groups']

        if self.plugin_config.JOIN_ALL_CHANS:
            for chan in channels:
                self.slack.channels.join(chan['name'])
                print('Joined', chan['name'])
            # for grp in groups:
            #     self.slack.groups.join(grp['name'])
        elif:
            for chan_name in self.plugin_config.CHANNELS:
                self.slack.channels.join(chan_name, validate=True)
                print('Joined', chan_name)

        print(self.__class__.__name__, 'initialized')
