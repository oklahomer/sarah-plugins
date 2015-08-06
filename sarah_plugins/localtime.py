# -*- coding: utf-8 -*-

import requests
import logging
from furl import furl
import json
from sarah.hipchat import HipChat
from typing import Dict


@HipChat.command('.localtime')
def hipchat_localtime(msg: HipChat.CommandMessage, config: Dict) -> str:
    furl_obj = furl('https://api.worldweatheronline.com/free/v2/tz.ashx', True)
    furl_obj.add(args={'format': 'json',
                       'key': config.get('api_key', ''),
                       'q': msg.text})

    try:
        response = requests.request('GET', furl_obj.url)

        # Avoid "can't use a string pattern on a bytes-like object"
        # j = json.loads(response.content)
        decoded_content = json.loads(response.content.decode())
    except requests.HTTPError as e:
        logging.error(e)
        return 'Request error.'
    except Exception as e:
        logging.error(e)
        return 'Unknown error occurred.'

    data = decoded_content.get('data', None)
    if data is None:
        logging.error('Malformed response %s', response.content)
        return 'Malformed response'
    elif 'error' in data:
        try:
            error_msg = data['error'][0].get('msg', '')
            return 'Error returned: %s' % error_msg
        except LookupError as e:
            logging.error('Invalid response %s %s', e, response.content)
            return 'Malformed error message returned'

    try:
        return ('Current time at %s is %s\nUTC offset is %s' %
                (
                    data['request'][0]['query'],
                    data['time_zone'][0]['localtime'],
                    data['time_zone'][0]['utcOffset']
                ))
    except LookupError as e:
        logging.error('Malformed response %s %s', e, response.content)
        return 'Malformed response'
