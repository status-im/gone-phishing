from __future__ import print_function
from rtmbot.core import Plugin, Job
import requests
from gglsbl import SafeBrowsingList

try:
    from urlparse import urlparse
except:
    from urllib.parse import urlparse

class URLMonitor(Plugin):

    blacklist = []
    moderators = []
    sbl = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.moderators = self.plugin_config['MODERATORS']

        # Initialize Safe Browsing API
        if self.plugin_config['GOOGLE_SAFE_BROWSING']:
            self.sbl = SafeBrowsingList(self.plugin_config['GOOGLE_SAFE_BROWSING_API_KEY'])
            self.sbl.update_hash_prefix_cache()

        # Populate Blacklist from URLS
        for url in self.plugin_config['BLACKLISTS']:
            url = url.strip()
            if url.endswith('.json'):
                r = requests.get(url)
                # Assuming MEW List format
                for item in r.json():
                    self.blacklist.append(item['id'])

            elif url.endswidth('.csv'):
                print('csv not implemented') # TODO
            else:
                print('txt not implement') # TODO

        print(self.__class__.__name__, 'initialized')

    def process_message(self, data):
        # print(data)
        # Private (Groups) or Public Channels
        if chan.startswith('C') or chan.startswith('G'):
            chan = data['channel']
            text = data['text']

            # Find all URLS in message text, extract host and compare against blacklist and Google Safebrowsing
            urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)

            def alert(url):
                # TODO flag user
                # TODO early warning system
                self.slack_client.api_call('chat.postMessage', channel=self.plugin_config['MODERATE_CHAN'], ' '.join(self.moderators) + ' ' + text) # TODO can probably use outputs for this
                if len(self.plugin_config.WARNING_MESSAGE):
                    self.outputs.append( [data['channel'], self.plugin_config.WARNING_MESSAGE] )

            for u in urls:
                o = urlparse(u)
                host = re.split(":\d{,4}", o.netloc)[0]

                # Check Blacklist
                if host in self.blacklist:
                    alert(u)
                    break
                # Check Google Safebrowsing
                elif sbl.lookup_url(u):
                    alert(u)
                    break
