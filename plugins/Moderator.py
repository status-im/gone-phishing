from __future__ import print_function
from rtmbot.core import Plugin
import time
import re
try:
    from urlparse import urlparse
except:
    from urllib.parse import urlparse

import requests
import glob, os
from PIL import Image
import imagehash
from StringIO import StringIO
from slack_scim import SlackSCIM

class Moderator(Plugin):

    flagged_users = {}
    eth_prog = re.compile(r'((0x)?[0-9a-fA-F]{40})')
    btc_prog = re.compile(r'([13][a-km-zA-HJ-NP-Z1-9]{25,34})')
    url_whitelist = ['contribute.status.im', 'test.status.im', 'slack.status.im', 'blog.status.im', 'status-im.slack.com', 'hackathon.status.im', 'contribute.status.im', 'status.im', 'www.status.im', 'wiki.status.im', 'artifacts.status.im', 'docs.status.im', 'www.bitcoinsuisse.ch', 'bitcoinsuisse.ch', 'i.diawi.com', 'commiteth.com', 'www.commiteth.com']
    user_whitelist = [] # truncated left as example
    user_blacklist = ['jarrad', 'jared', 'carl', 'hope', 'bennetts', 'status', 'vip', 'group', 'official' ] # truncated left as example
    id_whitelist = ['U4FASQ3PS'] # truncated left as example
    chan_whitelist = ['G2B3WG3LG', 'G5DA06HB7'] # truncated left as example
    time_lapse = 3600
    last_time = time.time()
    msg_count = 0
    msg_interval = 20


    def delete(self, data):
        self.slack_client.api_call(
                          "chat.delete",
                          channel=data['channel'],
                          ts=data['ts']
                        )

        info = self.slack_client.api_call('users.info', user=data['user'])
        name = info['user']['name']
        self.slack_client.api_call('chat.postMessage', channel='#internal-moderate', text=':warning: @{0} pasted an ETH/BTC address and message was deleted. :warning: `{1}`'.format(name, data['text']), as_user=True)
                                
    # def kill_user(self, data):
    #     # print('kill', data['text'].split('<@'))
    #     user_id = data['text'].split('<@')[1].split('>')[0].strip()
    #     if user_id not in self.id_whitelist:
    #         print('kill id', user_id)
    #         scim = SlackSCIM('') # < SCIM COST MONEY WTF?!
    #         scim.delete_user(user_id)
    #         # https://api.slack.com/scim#delete-users-id

    def process_message(self, data):
        print(data)

        # if data['text'].startswith('!kill') and data['channel'] == 'G2B41Q6AH':
        #     self.kill_user(data)

        now = time.time()
        elapsed = now - self.last_time
        
        # REPLACED WITH REMINDERS
        # if data['channel'] == 'C3NRE0L3U':
        #     self.msg_count += 1
        #     print('msg count', self.msg_count)
        #     if elapsed > self.time_lapse and self.msg_count > self.msg_interval:
        #         self.last_time = now
        #         self.msg_count = 0
        #         self.outputs.append(
        #             [data['channel'],
        #             ':warning: Be on the lookout for Scammers. There is *NO* presale or VIP group. Do not send your ETH/BTC to any address. We will *not* message you privately. https://contribute.status.im is the single source of truth. :warning:']
        #         )

        if data['user'] not in self.id_whitelist: # ignores trusted people
            chan = data['channel']
            if chan not in self.chan_whitelist: # internal channels are ignored
                if chan.startswith('C') or chan.startswith('G'): # group chats or channels

                    if '@channel' in data['text'] or '@here' in data['text'] or 'xn--status' in data['text']:
                        self.delete(data)
                        return

                    # delete anything that remotely looks like an eth or btc address, abit overzealous
                    eth_result = self.eth_prog.search(data['text'])
                    btc_result = self.btc_prog.search(data['text'])
                    if eth_result:
                        if eth_result.group(1):
                            self.delete(data)
                            return

                    if btc_result:
                        if btc_result.group(1):
                            self.delete(data)
                            return

                    # find any urls, if not approved host, then warn
                    urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', data['text'])
                    for u in urls:
                        o = urlparse(u)
                        host = re.split(":\d{,4}", o.netloc)[0]
                        if host not in self.url_whitelist:
                            self.outputs.append(
                                [data['channel'],
                                ':warning: Be careful clicking links. It may be safe to visit, but do not send your ETH or BTC to any address shown on unofficial websites. :warning:']
                            )
                            break

                    # identify imposters by image and name
                    # this should be on message and do user info lookup, but profile info is on join, so cheaper in terms of bandwidth.
                    # mostly ineffective as profile images are changed after join
                    if 'subtype' in data:
                        if data['subtype'] == 'channel_join': 
                            name = data['user_profile']['name']
                            img_url = data['user_profile']['image_72']
                            user_id = data['user']

                            print('checking', name)
                            suspicious = False
                            if name not in self.user_whitelist:
                                for b in self.user_blacklist:
                                    if b in name:
                                        suspicious = True
                                        print('BAD NAME', name)
                                        break

                            r = requests.get(img_url)
                            i = Image.open(StringIO(r.content))
                            user_hsh = imagehash.average_hash(i)
                            print('checking image', img_url, user_hsh)

                            for file in glob.glob("avatars/*.jpg"):
                                tmp, id, hsh = file[:-4].split('_')
                                hsh = imagehash.hex_to_hash(hsh)
                                # print(tmp, hsh, user_hsh)
                                if user_hsh == hsh:
                                    suspicious = True
                                    print('BAD IMAGE', tmp)
                                    break
                            print('suspicious', name, suspicious)
                            if suspicious:
                                if name not in self.flagged_users:
                                    self.slack_client.api_call('chat.postMessage', channel='#internal-moderate', text=':warning: @{} looks suspicious to me. :warning:'.format(name), as_user=True)
                                    self.flagged_users[name] = 1
                    