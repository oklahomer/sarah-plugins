# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from plotly.graph_objs import Data, Scatter
from plotly.plotly import plotly
from plotly.tools import FigureFactory

import requests
import logging
import json
from sarah.bot.slack import Slack, SlackMessage, MessageAttachment
from sarah.bot.values import CommandMessage
from typing import Dict


class BarchartClient(object):
    def __init__(self,
                 token: str,
                 base_url: str="http://marketdata.websol.barchart.com/"):
        self.token = token
        self.base_url = base_url

    def generate_endpoint(self, method: str) -> str:
        # http://www.barchartondemand.com/api.php
        return "%s%s.json" % (self.base_url, method)

    def get(self, method: str, params: Dict=None):
        params = params if params else dict()
        params.update({'key': self.token})
        endpoint = self.generate_endpoint(method)

        try:
            response = requests.get(endpoint, params)
            decoded_content = json.loads(response.content.decode())
            if int(decoded_content['status']['code']) == 200:
                return decoded_content
            else:
                raise Exception("Something went wrong %s" % response.content)
        except Exception as e:
            logging.error(e)
            raise

    def get_history(self, symbol):
        start_date = datetime.today() - timedelta(days=30)
        return self.get("getHistory",
                        {'symbol': symbol,
                         'startDate': start_date.strftime("%Y-%m-%dT00:00:00"),
                         'order': "desc",
                         'type': "daily"})


@Slack.command(".stock")
def slack_stock_price(msg: CommandMessage, config: Dict):
    if len(msg.text) > 1:
        try:
            response = BarchartClient(config.get('api_key', '')) \
                .get_history(msg.text.upper())
        except:
            # API request error
            # Already logged in BarchartClient, so just return error message.
            return "Something went wrong with %s" % msg.text
        else:
            try:
                open_prices = []
                high_prices = []
                low_prices = []
                close_prices = []
                dates = []
                volumes = []
                for result in response['results']:
                    open_prices.append(result['open'])
                    high_prices.append(result['high'])
                    low_prices.append(result['low'])
                    close_prices.append(result['close'])
                    dates.append(result['tradingDay'])
                    volumes.append(result['volume'])

                candle_graph_url = plotly.plot(
                    FigureFactory.create_candlestick(open_prices,
                                                     high_prices,
                                                     low_prices,
                                                     close_prices,
                                                     dates=dates),
                    filename="barchart/price_" + dates[-1],
                    vadlidate=False)

                volume_graph_url = plotly.plot(
                    Data([Scatter(x=dates,
                                  y=volumes)]))

                attachments = [
                    MessageAttachment(fallback="stock price history",
                                      title="stock price history",
                                      title_link=candle_graph_url,
                                      image_url=candle_graph_url + ".png"),
                    MessageAttachment(fallback="volume history",
                                      title="volume history",
                                      title_link=volume_graph_url,
                                      image_url=volume_graph_url + ".png")]

                return SlackMessage(
                    text="Stock price history for %s" % msg.text,
                    attachments=attachments)
            except Exception as e:
                # Response handling error
                logging.error(e)
                return "Something went wrong with %s" % msg.text

    else:
        return "Please enter ticker symbol."
