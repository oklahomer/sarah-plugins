# -*- coding: utf-8 -*-

import requests
import logging
from furl import furl
import json
from sarah.bot.hipchat import HipChat
from sarah.bot.slack import SlackMessage, Slack, MessageAttachment, \
    AttachmentField
from sarah.bot.values import CommandMessage
from typing import Dict


class WorldWeather(object):
    @staticmethod
    def request(api_key: str, query: str):
        furl_obj = furl(
            'http://api.worldweatheronline.com/free/v2/weather.ashx', True)

        furl_obj.add(args={'format': 'json',
                           'key': api_key,
                           'q': query})

        try:
            response = requests.request('GET', furl_obj.url)

            # Avoid "can't use a string pattern on a bytes-like object"
            # j = json.loads(response.content)
            decoded_content = json.loads(response.content.decode())
        except Exception as e:
            logging.error(e)
            raise

        data = decoded_content.get('data', None)
        if data is None:
            logging.error('Malformed response %s', response.content)
            raise Exception()
        elif 'error' in data:
            try:
                logging.error(data['error'][0].get('msg', ''))
            except Exception as e:
                logging.error("Invalid response %s %s", e, response.content)
            finally:
                raise Exception()

        return data


@HipChat.command('.weather')
def hipchat_weather(msg: CommandMessage, config: Dict) -> str:
    try:
        data = WorldWeather.request(config.get('api_key', ''), msg.text)
    except:
        return "Something went wrong with weather API"
    else:
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
            logging.error('Malformed response %s %s', e, data)
            return 'Error on parsing response.'


@Slack.command('.weather')
def hipchat_weather(msg: CommandMessage, config: Dict) -> str:
    try:
        data = WorldWeather.request(config.get('api_key', ''), msg.text)
    except:
        return "Something went wrong with weather API"
    else:
        try:
            condition = data['current_condition'][0]
            forecast = data['weather'][0]
            astronomy = forecast['astronomy'][0]

            description = "Current weather at %s is %s." % (
                data['request'][0]['query'],
                condition['weatherDesc'][0]['value'])

            return SlackMessage(
                attachments=[
                    # Current Condition
                    # Overall description
                    MessageAttachment(
                        fallback=description,
                        pretext="Current Condition",
                        title=description,
                        color="#32CD32",
                        image_url=condition['weatherIconUrl'][0]['value']),

                    # Temperature
                    MessageAttachment(
                        fallback="Temperature: %s degrees Celsius." %
                                 condition['temp_C'],
                        title="Temperature",
                        color="#32CD32",
                        fields=[
                            AttachmentField(title="Fahrenheit",
                                            value=condition['temp_F'],
                                            short=True),
                            AttachmentField(title="Celsius",
                                            value=condition['temp_C'],
                                            short=True)]),

                    # Wind Speed
                    MessageAttachment(
                        fallback="Wind speed: %s Km/h" %
                                 condition['windspeedKmph'],
                        title="Wind Speed",
                        color="#32CD32",
                        fields=[
                            AttachmentField(title="mi/h",
                                            value=condition['windspeedMiles'],
                                            short=True),
                            AttachmentField(title="km/h",
                                            value=condition['windspeedKmph'],
                                            short=True)]),

                    # Humidity
                    MessageAttachment(
                        fallback="Humidity: %s %%" % condition['humidity'],
                        title="Humidity",
                        color="#32CD32",
                        fields=[
                            AttachmentField(title="Percentage",
                                            value=condition['humidity'],
                                            short=True)]),

                    # Forecast
                    # Sunrise / Sunset
                    MessageAttachment(
                        fallback="Sunrise at %s. Sunset at %s." % (
                            astronomy['sunrise'], astronomy['sunset']),
                        pretext="Forecast",
                        title="",
                        color="#006400",
                        fields=[
                            AttachmentField(
                                title="Sunrise",
                                value=astronomy['sunrise'],
                                short=True),
                            AttachmentField(
                                title="Sunrise",
                                value=astronomy['sunset'],
                                short=True)]),

                    # Moonrise / Moonset
                    MessageAttachment(
                        fallback="Moonrise at %s. Moonset at %s." % (
                            astronomy['moonrise'], astronomy['moonset']),
                        title="",
                        color="#006400",
                        fields=[
                            AttachmentField(
                                title="Moonrise",
                                value=astronomy['moonrise'],
                                short=True),
                            AttachmentField(
                                title="Moonset",
                                value=astronomy['moonset'],
                                short=True)])])

        except LookupError as e:
            logging.error('Malformed response %s %s', e, data)
            return 'Error on parsing response.'
