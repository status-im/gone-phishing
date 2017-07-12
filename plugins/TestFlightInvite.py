from __future__ import print_function
from rtmbot.core import Plugin
import time
from email.utils import parseaddr
from dns.resolver import query

import json
import urllib
import urllib2
import cookielib
import re
import sys
import os
from getpass import getpass

# TestFlight Inviter
# Copyright 2014-2015 Brian Donohue
#
# Version 1.0
#
# Latest version and additional information available at:
#   http://appdailysales.googlecode.com/
#
# This script will automate TestFlight invites for Apple's TestFlight integration.
#
# This script is heavily based off of appdailysales.py (https://github.com/kirbyt/appdailysales)
# Original Maintainer
#   Kirby Turner
#
# Original Contributors:
#   Leon Ho
#   Rogue Amoeba Software, LLC
#   Keith Simmons
#   Andrew de los Reyes
#   Maarten Billemont
#   Daniel Dickison
#   Mike Kasprzak
#   Shintaro TAKEMURA
#   aaarrrggh (Paul)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

class ITCException(Exception):
    def __init__(self,value):
        self.value = value
    def __str__(self):
        return repr(self.value);

class TFInviteDuplicateException(Exception):
    pass

# There is an issue with Python 2.5 where it assumes the 'version'
# cookie value is always integer.  However, itunesconnect.apple.com
# returns this value as a string, i.e., "1" instead of 1.  Because
# of this we need a workaround that "fixes" the version field.
#
# More information at: http://bugs.python.org/issue3924
class MyCookieJar(cookielib.CookieJar):
    def _cookie_from_cookie_tuple(self, tup, request):
        name, value, standard, rest = tup
        version = standard.get('version', None)
        if version is not None:
            version = version.replace('"', '')
            standard["version"] = version
        return cookielib.CookieJar._cookie_from_cookie_tuple(self, tup, request)

class iTunesConnect:
    urlITCBase = 'https://itunesconnect.apple.com%s'

    def __init__(self, itcLogin, itcPassword, appId, proxy='', groupId=None, contentProviderId=None):
        self.itcLogin = itcLogin
        self.itcPassword = itcPassword
        self.appId = str(appId)
        self._service_key = None
        self.proxy = proxy
        self.groupId = groupId
        self.contentProviderId = contentProviderId
        self.opener = self.createOpener()
        self.loggedIn = False

    def readData(self, url, data=None, headers={}, method=None):
        request = urllib2.Request(url, data, headers)
        if method is not None:
            request.get_method = lambda: method
        urlHandle = self.opener.open(request)
        return urlHandle.read()

    def createOpener(self):
        handlers = []                                                       # proxy support
        if self.proxy:                                                      # proxy support
            handlers.append(urllib2.ProxyHandler({"https": self.proxy}))    # proxy support

        cj = MyCookieJar();
        cj.set_policy(cookielib.DefaultCookiePolicy(rfc2965=True))
        cjhdr = urllib2.HTTPCookieProcessor(cj)
        handlers.append(cjhdr)                                              # proxy support
        return urllib2.build_opener(*handlers)                              # proxy support

    @property
    def service_key(self):
        if self._service_key:
            return self._service_key

        jsUrl = self.urlITCBase % '/itc/static-resources/controllers/login_cntrl.js'
        content = self.readData(jsUrl)
        matches = re.search(r"itcServiceKey = '(.*)'", content)
        if not matches:
            raise ValueError('Unable to find iTunes Connect Service key')
        return matches.group(1)

    def getGroups(self):
        text = self.readData('https://itunesconnect.apple.com/testflight/v2/providers/{teamId}/apps/{appId}/groups'.format(
            teamId=self.contentProviderId, appId=self.appId
        ))
        data = json.loads(text)
        return data['data']

    def getDefaultExternalGroupId(self):
        self.groupData = self.getGroups()
        for group in self.groupData:
            if group['isDefaultExternalGroup']:
                return group['id']
        return None

    def getFirstContentProviderId(self):
        # Sample return value
        # => {"associatedAccounts"=>
        #   [{"contentProvider"=>{"contentProviderId"=>11142800, "name"=>"Felix Krause", "contentProviderTypes"=>["Purple Software"]}, "roles"=>["Developer"], "lastLogin"=>1468784113000}],
        #  "sessionToken"=>{"dsId"=>"8501011116", "contentProviderId"=>18111111, "expirationDate"=>nil, "ipAddress"=>nil},
        text = self.readData("https://itunesconnect.apple.com/WebObjects/iTunesConnect.woa/ra/user/detail")
        data = json.loads(text)
        account = data['data']['associatedAccounts'][0]
        return account['contentProvider']['contentProviderId']

    def login(self):
        if self.loggedIn:
            return

        data = {
            'accountName': self.itcLogin,
            'password': self.itcPassword,
            'rememberMe': 'false'
        }
        headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json, text/javascript'
        }
        
        loginUrl = 'https://idmsa.apple.com/appleauth/auth/signin?widgetKey=%s' % self.service_key
        self.readData(
            'https://idmsa.apple.com/appleauth/auth/signin?widgetKey=%s' % self.service_key,
            data=json.dumps(data),
            headers=headers
        )
        
        if not self.contentProviderId:
            self.contentProviderId = self.getFirstContentProviderId()
        if not self.groupId:
            self.groupId = self.getDefaultExternalGroupId()

        self.loggedIn = True

    def numTesters(self):
        self.login()
        endpoint = '/WebObjects/iTunesConnect.woa/ra/user/externalTesters/%s/' % self.appId
        urlWebsiteExternalTesters = self.urlITCBase % endpoint
        externalResponse = self.readData(
            "https://itunesconnect.apple.com/WebObjects/iTunesConnect.woa/ra/user/externalTesters/%s/" % self.appId,
            headers={'Content-Type': 'application/json'}
        )
        data = json.loads(externalResponse)
        return len(data['data']['users'])

    def addTester(self, email, firstname='', lastname=''):
        self.login()
        params = { 'email': email, 'firstName': firstname, 'lastName': lastname }
        text = self.readData(
            'https://itunesconnect.apple.com/testflight/v2/providers/{teamId}/apps/{appId}/testers'.format(
                teamId=self.contentProviderId, appId=self.appId
            ),
            json.dumps(params),
            headers={'Content-Type': 'application/json'}
        )

        testerResponseBody = json.loads(text)
        testerId = testerResponseBody['data']['id']
        params = {
            'groupId': self.groupId,
            'testerId': testerId,
        }

        return self.readData(
            'https://itunesconnect.apple.com/testflight/v2/providers/{teamId}/apps/{appId}/groups/{groupId}/testers/{testerId}'.format(
                teamId=self.contentProviderId, appId=self.appId, groupId=self.groupId, testerId=testerId
            ),
            json.dumps(params),
            headers={'Content-Type': 'application/json'},
            method='PUT'
        )

# https://github.com/Donohue/testflight_invite

class TestFlightInvite(Plugin):

    needles = ['ios', 'download', 'testflight']
    itunes = iTunesConnect('', '', 0) # FILL THIS IN 


    def process_message(self, data):
        chan = data['channel']
        if chan.startswith('D'):
            # print(data)
            msg = data['text']
            pos = msg.find('<mailto:')
            if pos != -1:
                email = msg.strip()[pos+8:].split('|')[0]
                print('Found email in message', email)
                if '@' in parseaddr(email)[1]:
                    domain = email.rsplit('@', 1)[-1]
                    if bool(query(domain, 'MX')):
                        try:
                            self.itunes.addTester(email, '', '')
                            self.outputs.append(
                                [data['channel'],
                                "Invite Sent! Thanks for being daring enough to try out Status in alpha, and please shake your phone and send in any bugs :slightly_smiling_face:" ]
                            )
                        except TFInviteDuplicateException as e:
                            self.outputs.append(
                                [data['channel'],
                                'Hmm, seems we already have sent out an invite to that email']
                            )
                        except Exception as e:
                            print('Invite Failed: %s' % str(e))
                    else:
                        self.outputs.append(
                            [data['channel'],
                            'Hmm there is no MX records on that domain?']
                        )