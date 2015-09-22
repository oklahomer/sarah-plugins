# -*- coding: utf-8 -*-
import json
import logging
import requests
import re
from sarah.bot.slack import Slack, MessageAttachment, SlackMessage, \
    AttachmentField
from sarah.bot.values import CommandMessage, UserContext, InputOption
from typing import Dict, Sequence, Union
from plotly.graph_objs import Data, Scatter
from plotly.plotly import plotly


class FixerClient(object):
    def __init__(self,
                 base_url: str="http://api.fixer.io/"):
        self.base_url = base_url

    def generate_endpoint(self, path: str) -> str:
        return "%s%s" % (self.base_url, path)

    def get(self, path: str, params: Dict=None) -> Dict:
        params = params if params else dict()
        endpoint = self.generate_endpoint(path)

        try:
            response = requests.get(endpoint, params)
            decoded_content = json.loads(response.content.decode())
            return decoded_content
        except Exception as e:
            logging.error(e)
            raise

    def get_current_rate(self,
                         base: str="USD",
                         symbols: Sequence[str]=None) -> Dict:

        params = {'base': base}
        if symbols:
            params.update({'symbols': ",".join(symbols)})

        return self.get("latest", params)

    def convert(self,
                amount: int,
                from_currency: str,
                to_currency: str) -> Dict:

        rate = self.get_current_rate(
            to_currency,
            [from_currency])['rates'][from_currency]

        return {'converted_amount': "%.2f" % (float(amount) / rate),
                'rate': rate}


class ExchangeRateLabClient(object):
    def __init__(self,
                 token: str,
                 base_url: str="http://api.exchangeratelab.com/api/"):
        self.token = token
        self.base_url = base_url

    def generate_endpoint(self, target: str) -> str:
        # http://www.exchangeratelab.com/docs
        return "%s%s" % (self.base_url, target)

    def get(self, target: str, params: Dict=None) -> Dict:
        params = params if params else dict()
        params.update({'apikey': self.token})
        endpoint = self.generate_endpoint(target)

        try:
            response = requests.get(endpoint, params)
            decoded_content = json.loads(response.content.decode())
            return decoded_content
        except Exception as e:
            logging.error(e)
            raise

    def get_current_top8(self, base_currency: str) -> Dict:
        # https://gist.github.com/anonymous/223204059a31e80a2dab
        return self.get("current/%s" % base_currency)

    def get_weekly(self, currency: str) -> Dict:
        # https://gist.github.com/anonymous/e2d493d8d12948437ff0
        return self.get("history/week", {'curr': currency})


@Slack.command('.currency')
def slack_currency(msg: CommandMessage,
                   config: Dict) -> Union[str, UserContext]:
    regex = re.compile(r'''
        (\d+(?:\.\d+)?)        # Decimal number
        \s*([a-zA-Z]{3})       # 3-letter currency code
        \s+(?:in|as|of|to)\s+  # preposition
        ([a-zA-Z]{3})          # 3-letter currency code
        ''', re.VERBOSE)
    match = regex.match(msg.text)

    if not match:
        help_message = (
            "Please input command in a form below:\n"
            ".currency {AMOUNT_NUMBER} {BASE_CURRENCY} to {TARGET_CURRENCY}\n"
            "e.g. .currency 100 JPY to USD")
        return UserContext(message=help_message,
                           help_message=help_message,
                           input_options=(InputOption(".", slack_currency), ))

    amount, of, to = match.groups()
    try:
        data = FixerClient().convert(amount, of, to)
    except:
        return "Something went wrong. Input: %s" % msg.text
    else:
        return "%s (1%s = %s%s)" % (data['converted_amount'],
                                    to,
                                    data['rate'],
                                    of)


@Slack.schedule('summary_report')
def summary_report(config: Dict) -> Union[str, SlackMessage]:
    try:
        client = ExchangeRateLabClient(config['exchange_rate_lab_api_key'])

        # Currency rates for past one week
        scatters = []
        # for currency in ['AUD', 'CAD', 'CNY', 'EUR', 'GBP', 'INR', 'JPY']:
        for currency in ['JPY']:
            data = client.get_weekly(currency)
            scatters.append(Scatter(
                x=[daily['dateCurrencyRate'] for daily in data['currencies']],
                y=[daily['amountTo'] for daily in data['currencies']],
                name=currency,
                mode='lines+markers'
            ))
        weekly_plot_url = plotly.plot(Data(scatters))
        attachments = [
            MessageAttachment(fallback="Currency rate history",
                              pretext="Currency rate history",
                              title="Base currency: USD",
                              title_link=weekly_plot_url,
                              image_url=weekly_plot_url + ".png")]

        # Add current rates
        current_top8 = client.get_current_top8("JPY")
        fields = [AttachmentField(r['to'],
                                  "%.4f" % (float(1)/r['rate']),
                                  True)
                  for r in current_top8['rates']]
        attachments.append(MessageAttachment(fallback="Current currency rate",
                                             pretext="Current currency rate",
                                             title="Base currency: JPY.",
                                             fields=fields))

        return SlackMessage(
            text="Summary Report",
            attachments=attachments)
    except:
        return "Something went wrong"
