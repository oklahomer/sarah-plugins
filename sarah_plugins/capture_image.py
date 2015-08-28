# -*- coding: utf-8 -*-

import requests
import logging
import json
from sarah.bot.hipchat import HipChat
from sarah.bot.values import CommandMessage
from typing import Dict


@HipChat.command('.capture_image')
def capture_image(_: CommandMessage, config: Dict) -> str:
    try:
        response = requests.request('GET', config.get('endpoint', ''))
    except requests.HTTPError as e:
        logging.error(e)
        return 'Request error.'
    except Exception as e:
        logging.error(e)
        return 'Unknown error occurred.'

    try:
        # Avoid "can't use a string pattern on a bytes-like object"
        # j = json.loads(response.content)
        decoded_content = json.loads(response.content.decode())
    except Exception as e:
        logging.error(e)
        return 'Error on parsing response.'

    return decoded_content['url']
