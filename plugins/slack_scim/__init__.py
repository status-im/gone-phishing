# -*- mode: python; coding: utf-8; -*-
"""
This module implements Slack SCIM API in Python.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

__author__ = "Anatoly Bardukov"
__version__ = "0.1"

import json
import six

import requests
import logging
from copy import copy

if six.PY3:
    from urllib.parse import urljoin
else:
    from urlparse import urljoin

SLACK_SCIM_API_ENDPOINT = 'https://api.slack.com/scim/v1/'
SLACK_USER_ID_ENDPOINT = 'Users/%s'
SLACK_USERS_ENDPOINT = 'Users'
SLACK_GROUP_ID_ENDPOINT = 'Groups/%s'
SLACK_GROUPS_ENDPOINT = 'Groups'


class BaseAPIException(Exception):
    pass


class BaseAPI(object):
    def __init__(self, headers=None, api_link=''):
        if headers is None:
            headers = {}
        self.headers = headers
        self.api_link = api_link

    def _request(self, method, endpoint, params=None, data=None):
        logging.debug('Sending %s request to %s' % (method, endpoint))
        response = requests.request(
            method,
            urljoin(self.api_link, endpoint),
            headers=self.headers,
            params=params,
            data=data
        )

        if not response.ok:
            raise BaseAPIException('Request error: %s, %s' %
                                   (response.status_code, response.text))

        return response

    def _get(self, endpoint, params=None):
        return self._request('get', endpoint, params)

    def _post(self, endpoint, params=None, data=None):
        return self._request('post', endpoint, params, data)

    def _delete(self, endpoint, params=None):
        return self._request('delete', endpoint, params)

    def _put(self, endpoint, params=None, data=None):
        return self._request('put', endpoint, params, data)

    def _patch(self, endpoint, params=None, data=None):
        return self._request('patch', endpoint, params, data)


class SlackSCIMException(Exception):
    pass


class User(object):
    def __init__(self, params, scim_api):
        self.params = params
        self.schemas = params.get('schemas', ["urn:scim:schemas:core:1.0"])
        self.scim_api = scim_api
        self.id = params.get('id', str())
        self.userName = params.get('userName', str())
        self.nickName = params.get('nickName', str())
        self.title = params.get('title', str())
        self.name = params.get('name', {})
        self.emails = params.get('emails', [])
        self.groups = params.get('groups', [])
        self.active = params.get('active', True)
        self.json_fields = ('id', 'userName', 'nickName', 'title',
                            'schemas', 'name', 'emails', 'groups')

    @classmethod
    def from_string(cls, string, scim_api):
        js = json.loads(string)
        return cls(js, scim_api)

    def __getitem__(self, item):
        return getattr(self, item,
                       self.params.get(item, None))

    def add_mail(self, value, display='', type='', primary=False):
        email = {'value': value}

        if display:
            email['display'] = display

        if type:
            email['type'] = type

        if primary:
            email['primary'] = primary

        self.emails.append(email)

        self.save()
        return self.emails

    def delete_mail(self, value):
        for mail in self.emails:
            if mail['value'] == value:
                del mail
                break

        self.save()
        return self.emails

    @property
    def json(self):
        return {attr: getattr(self, attr)
                for attr in self.json_fields}

    def __str__(self):
        return json.dumps(self.json)

    def __repr__(self):
        return '<SlackSCIM User object: %s>' % self.id

    def check_id(self):
        if not self.id:
            raise SlackSCIMException("Missing user's id")

    def check_username(self):
        if not self.userName:
            raise SlackSCIMException("Missing userName (%s)" % self.id)

    def check_emails(self):
        if not self.emails:
            raise SlackSCIMException(
                "User (%s) must have at least 1 email" % self.id)

        for email in self.emails:
            if not email['value']:
                raise SlackSCIMException(
                    "User's (%s) email does not have value" % self.id)

    def check_groups(self):
        for group in self.groups:
            if not group['value']:
                raise SlackSCIMException(
                    "User's (%s) group must have value" % self.id)

    def check(self):
        checks = filter(lambda x: x.startswith('check_'), dir(self))
        for check in checks:
            getattr(self, check)()

        return True

    def save(self, force=False):
        if self.check():
            if force:
                self.scim_api.put_user(self.id, str(self))
            else:
                self.scim_api.patch_user(self.id, str(self))
            return True
        return False

    def delete(self):
        self.scim_api.delete_user(self.id)
        self.id = ''
        self.scim_api = None

    def disable(self):
        data = {
            'schemas': ["urn:scim:schemas:core:1.0"],
            'id': self.id,
            'active': False,
            'emails': [self.primary_email]
        }
        self.scim_api.patch_user(self.id, json.dumps(data))
        self.update()
        return self

    def activate(self):
        data = {
            'schemas': ["urn:scim:schemas:core:1.0"],
            'id': self.id,
            'active': True,
            'emails': [self.primary_email]
        }
        self.scim_api.patch_user(self.id, json.dumps(data))
        self.update()
        return self

    def update(self, params=None, fields=None):
        if fields is None:
            fields = ['userName', 'nickName', 'title',
                      'name', 'emails', 'groups']
        if params:
            data = {"schemas": ["urn:scim:schemas:core:1.0"]}
            for field in params.keys():
                data[field] = params[field]

            actual_user = self.scim_api.patch_user(self.id, json.dumps(data))
        else:
            actual_user = self.scim_api.get_user(self.id)

        for field in fields:
            setattr(self, field, getattr(actual_user, str(field)))

        return self

    @property
    def primary_email(self):
        for email in self.emails:
            if email['primary']:
                return email


class Group(object):
    def __init__(self, params, scim_api):
        self.params = params
        self.schemas = params.get('schemas', ["urn:scim:schemas:core:1.0"])
        self.scim_api = scim_api
        self.id = params.get('id', str())
        self.displayName = params.get('displayName', str())
        self.members = params.get('members', [])
        self.json_fields = ('id', 'schemas', 'displayName', 'members')

    def __getitem__(self, item):
        return getattr(self, item,
                       self.params.get(item, None))

    @classmethod
    def from_string(cls, string, scim_api):
        js = json.loads(string)
        return cls(js, scim_api)

    def add_members(self, users):
        if not isinstance(users, list):
            users = [users]

        for user in users:
            user_id = getattr(user, str('id'), str(user))
            self.members.append({'value': user_id})

        self.save()
        return self.members

    def delete_members(self, users):
        """
        Delete members from usergroup
        :param users: one or list of User objects or ids
        :return: members list
        """
        if not isinstance(users, list):
            users = [users]
        user_ids = [getattr(user, str('id'), str(user)) for user in users]

        to_delete = []
        for us in self.members:
            if str(us['value']) in user_ids:
                to_delete.append({'value': copy(us['value']),
                                  'operation': 'delete'})
                del us
        self.update({'members': to_delete})
        return self.members

    @property
    def json(self):
        return {attr: getattr(self, attr)
                for attr in self.json_fields}

    def __str__(self):
        return json.dumps(self.json)

    def __repr__(self):
        return '<SlackSCIM Group object: %s>' % self.id

    def check_id(self):
        if not self.id:
            raise SlackSCIMException("Missing groups's id")

    def check_displayname(self):
        if not self.displayName:
            raise SlackSCIMException(
                "Group (%s) must have displayName" % self.id)

    def check_members(self):
        for member in self.members:
            if not member['value']:
                raise SlackSCIMException(
                    "Members of a group (%s) must have value" % self.id
                )

    def check(self):
        checks = filter(lambda x: x.startswith('check_'), dir(self))
        for check in checks:
            getattr(self, check)()

        return True

    def save(self, force=False):
        if self.check():
            if force:
                self.scim_api.put_group(self.id, str(self))
            else:
                self.scim_api.patch_group(self.id, str(self))
            return True
        return False

    def delete(self):
        self.scim_api.delete_group(self.id)
        del self

    def update(self, params=None, fields=None):
        if fields is None:
            fields = ['members', 'displayName']

        if params:
            data = {"schemas": ["urn:scim:schemas:core:1.0"]}
            for field in params.keys():
                data[field] = params[field]

            self.scim_api.patch_group(self.id, json.dumps(data))

        actual_group = self.scim_api.get_group(self.id)

        for field in fields:
            setattr(self, field, getattr(actual_group, str(field)))

        return self


class SlackSCIM(BaseAPI):
    def __init__(self, token, endpoint=SLACK_SCIM_API_ENDPOINT):
        self.token = token
        super(SlackSCIM, self).__init__(
            {
                'Authorization': 'Bearer %s' % token,
                'Content-type': 'application/json'
            }, endpoint
        )
        self.users = []
        self.groups = []
        self.refresh()

    def refresh(self):
        self.users = self.get_users()
        self.groups = self.get_groups()

    def get_user(self, user_id):
        return User.from_string(
            self._get(SLACK_USER_ID_ENDPOINT % str(user_id)).content,
            self)

    def get_users(self, per_page=10, start_index=1):
        users = []
        while True:
            response = json.loads(
                self._get(SLACK_USERS_ENDPOINT,
                          params={'startIndex': start_index,
                                  'count': per_page
                                  }).content)

            users.extend(
                [User(user, self) for user in response['Resources']]
            )

            start_page += per_page
            if start_page > response['totalResults']:
                break

        self.users = users
        return self.users

    def get_active_users(self):
        return [u for u in self.get_users() if u.active]

    def create_user(self, params):
        data = {
            'schemas': ["urn:scim:schemas:core:1.0"],
            "userName": params['username'],
            "nickName": params['nickname'],
            "name": {
                "givenName": params.get('givenname'),
                "familyName": params.get('familyname')
            },
            'displayName': params.get('displayName', ''),
            "title": params.get('title', "Mr."),
            "emails": [{
                "value": params['mail'],
                "primary": True
            }],
        }
        return User.from_string(
            self._post(SLACK_USERS_ENDPOINT, data=json.dumps(data)).content,
            self
        )

    def put_user(self, user_id, data):
        return self._put(
            SLACK_USER_ID_ENDPOINT % str(user_id),
            data=data).content

    def patch_user(self, user_id, data):
        return self._patch(
            SLACK_USER_ID_ENDPOINT % str(user_id),
            data=data).content

    def delete_user(self, user_id):
        self._delete(SLACK_USER_ID_ENDPOINT % str(user_id))
        return

    def get_group(self, group_id):
        return Group.from_string(
            self._get(
                SLACK_GROUP_ID_ENDPOINT % str(group_id),
            ).content, self)

    def get_groups(self, per_page=10, start_index=0):
        groups = []
        while True:
            response = json.loads(
                self._get(SLACK_GROUPS_ENDPOINT,
                          params={'startIndex': start_index,
                                  'count': per_page
                                  }).content)

            groups.extend(
                [Group(group, self) for group in response['Resources']]
            )

            start_index += per_page
            if start_index > response['totalResults']:
                break

        self.groups = groups
        return self.groups

    def create_group(self, params, members=None):
        if members is None:
            members = []
        data = {
            'schemas': ["urn:scim:schemas:core:1.0"],
            'id': params.get('id', ''),
            'displayName': params['displayName'],
            'members': [{'value': getattr(u, 'id', str(u))} for u in members]
        }
        return Group.from_string(
            self._post(SLACK_GROUPS_ENDPOINT, data=json.dumps(data)).content,
            self)

    def put_group(self, group_id, data):
        return self._put(
            SLACK_GROUP_ID_ENDPOINT % str(group_id),
            data=data).content

    def patch_group(self, group_id, data):
        return self._patch(
            SLACK_GROUP_ID_ENDPOINT % str(group_id),
            data=data).content

    def delete_group(self, group_id):
        self._delete(SLACK_GROUP_ID_ENDPOINT % str(group_id))
        return
