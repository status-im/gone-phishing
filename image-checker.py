import requests
import shutil

from slacker import Slacker


import requests
import glob, os
from PIL import Image
import imagehash
from StringIO import StringIO

r = requests.get('')
i = Image.open(StringIO(r.content))
user_hsh = imagehash.average_hash(i)

for file in glob.glob("avatars/*.jpg"):
    name, id, hsh = file[:-4].split('_')
    hsh = imagehash.hex_to_hash(hsh)
    print(id)
    # if user_hsh == hsh:
    #     print(user_hsh - hsh, name, id, hsh)
    # hsh = imagehash.average_hash(Image.open(file))

    # parts = 

    # newfile = '{0}.jpg'.format(file[:-21])
    # shutil.move(file, newfile)
    # print(file[:-4] + '_' + str(hsh) + '.jpg')
    # print(newfile, str(hsh))

# slack = Slacker('')

# def get_users():
#     global slack
#     return [user for user in slack.users.list().body['members'] if user['deleted'] is False]


# users = get_users()

# for user in users:
#     if user['name'] == 'jarradhope':
#         print(user['profile'])
#         break
# #     r = requests.get(url, stream=True)
#     if r.status_code == 200:
#         with open('./avatars/{0}_{1}'.format(user['name'], user['id']), 'wb') as f:
#             r.raw.decode_content = True
#             shutil.copyfileobj(r.raw, f)
#         print(user['name'], url)
#     else:
#         print('failed', user['name'], url)