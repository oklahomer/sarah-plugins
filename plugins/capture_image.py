# -*- coding: utf-8 -*-

import requests
import logging
from requests.compat import json
from sarah.hipchat import HipChat


@HipChat.command('.capture_image')
def capture_image(msg, config):
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
