import json

settings = json.load(open('settings.json', 'r'))

channel_id = settings['channel_id']
channel_url = settings['channel_url']
admin_ids = settings['admin_ids']
token = settings['token']