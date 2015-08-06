# -*- coding: utf-8 -*-

import requests
import logging
from furl import furl
import json
from sarah.hipchat import HipChat
from typing import Dict


@HipChat.command('.weather')
def weather(msg: HipChat.CommandMessage, config: Dict) -> str:
    furl_obj = furl('http://api.worldweatheronline.com/free/v2/weather.ashx',
                    True)
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

    if 'data' not in decoded_content:
        logging.error('Invalid response %s', response.content)
        return 'Invalid response format.'

    if 'error' in decoded_content['data']:
        error_msg = decoded_content['data']['error'][0].get('msg', '')
        return 'Error returned: %s' % error_msg

    try:
        condition = decoded_content['data']['current_condition'][0]
        return ('Current weather at %s is %s\n'
                '%s degrees Celsius. %s degrees Fahrenheit.' %
                (
                    decoded_content['data']['request'][0]['query'],
                    condition['weatherDesc'][0]['value'],
                    condition['temp_C'],
                    condition['temp_F']
                ))
    except Exception as e:
        logging.error(e)
        return 'Error on parsing response.'
