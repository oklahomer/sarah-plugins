# -*- coding: utf-8 -*-

import requests
import logging
from furl import furl
import json
from sarah.bot.hipchat import HipChat
from sarah.bot.values import CommandMessage
from typing import Dict


@HipChat.command('.weather')
def weather(msg: CommandMessage, config: Dict) -> str:
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
        condition = data['current_condition'][0]
        return ('Current weather at %s is %s\n'
                '%s degrees Celsius. %s degrees Fahrenheit.' %
                (
                    data['request'][0]['query'],
                    condition['weatherDesc'][0]['value'],
                    condition['temp_C'],
                    condition['temp_F']
                ))
    except LookupError as e:
        logging.error('Malformed response %s %s', e, response.content)
        return 'Error on parsing response.'
