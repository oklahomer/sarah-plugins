# -*- coding: utf-8 -*-
import logging
import feedparser
import requests
from sarah import ValueObject
from sarah.bot.hipchat import HipChat

from sarah.bot.slack import Slack, SlackMessage, MessageAttachment, \
    AttachmentField
from sarah.bot.values import CommandMessage, UserContext, InputOption
from typing import Dict, Sequence, Union


class Entry(ValueObject):
    def __init__(self,
                 link: str,
                 title: str,
                 summary: str,
                 bookmark_count: int):
        pass

    @property
    def link(self) -> str:
        return self['link']

    @property
    def title(self) -> str:
        return self['title']

    @property
    def summary(self) -> str:
        return self['summary']

    @property
    def bookmark_count(self) -> int:
        return self['bookmark_count']


class Feed(ValueObject):
    def __init__(self,
                 category: str,
                 entries: Sequence[Entry]):
        pass

    @property
    def category(self) -> str:
        return self['category']

    @property
    def entries(self) -> Sequence[Entry]:
        return self['entries']


class CachedContent(ValueObject):
    def __init__(self,
                 feed: Feed,
                 gist_url: str):
        pass

    @property
    def feed(self) -> Feed:
        return self['feed']

    @property
    def gist_url(self) -> str:
        return self['gist_url']


class Hateb(object):
    def __init__(self):
        self.__cached_content = None

    @property
    def allowed_categories(self) -> Sequence[str]:
        return sorted(self.feed_map.keys())

    @property
    def feed_map(self) -> Dict:
        # Be careful, hotentry has original format of hotentry.rss
        # while the others have hotentry/{CATEGORY}.rss.
        return {'hotentry': "http://b.hatena.ne.jp/hotentry.rss",
                'general': "http://b.hatena.ne.jp/hotentry/general.rss",
                'social': "http://b.hatena.ne.jp/hotentry/social.rss",
                'economics': "http://b.hatena.ne.jp/hotentry/economics.rss",
                'life': "http://b.hatena.ne.jp/hotentry/life.rss",
                'knowledge': "http://b.hatena.ne.jp/hotentry/knowledge.rss",
                'it': "http://b.hatena.ne.jp/hotentry/it.rss",
                'fun': "http://b.hatena.ne.jp/hotentry/fun.rss",
                'entertainment': "http://b.hatena.ne.jp/hotentry/entertainment.rss",
                'game': "http://b.hatena.ne.jp/hotentry/game.rss"}

    def retrieve_feed(self, category: str) -> Feed:
        feed_url = self.feed_map[category]
        result = feedparser.parse(feed_url)

        if result['status'] != 200:
            logging.error('Response status: %d', result['status'])
            return 'Response status: %s' % result['status']

        return Feed(category=category,
                    entries=[Entry(e['link'],
                                   e['title'],
                                   e['summary'],
                                   int(e['hatena_bookmarkcount']))
                             for e in result['entries']])

    def is_new(self, feed: Feed) -> bool:
        if self.__cached_content:
            return self.__cached_content.feed != feed
        else:
            return True

    def post_gist(self, feed: Feed) -> str:
        if self.is_new(feed):
            content = '\n'.join(
                ['- [%s](%s) (%d)  \n%s  ' % (e.title,
                                              e.link,
                                              e.bookmark_count,
                                              e.summary)
                 for e in feed.entries])

            response = requests.post(
                'https://api.github.com/gists',
                json={'description': "hot entry",
                      'public': False,
                      'files': {'entries.md': {'content': content}}})

            gist_url = response.json()['html_url']
            self.__cached_content = CachedContent(feed, gist_url)

            return gist_url
        else:
            return self.__cached_content.gist_url


hateb = Hateb()


@Slack.command('.hateb')
def slack_hateb(msg: CommandMessage,
                _: Dict=None) -> Union[str, UserContext]:
    if msg.text in hateb.allowed_categories:
        feed = hateb.retrieve_feed(msg.text)
        gist_url = hateb.post_gist(feed)

        attachments = [
            MessageAttachment(
                fallback="[%d] %s : %s" % (e.bookmark_count,
                                           e.title,
                                           e.link),
                fields=[AttachmentField(title="Bookmark Count",
                                        value=str(e.bookmark_count))],
                title_link=e.link,
                title=e.title,
                color="#00FF00") for e in feed.entries[:10]]

        attachments.append(
            MessageAttachment(fallback="See more at %s" % gist_url,
                              title="See More",
                              title_link=gist_url))

        return SlackMessage(text="Category: %s" % msg.text,
                            attachments=attachments)
    else:
        message = ("Please choose a category from below:\n%s" %
                   ", ".join(hateb.allowed_categories))
        return UserContext(message=message,
                           help_message=message,
                           input_options=(InputOption(".", slack_hateb),))


@HipChat.command('.hateb')
def hipchat_hateb(msg: CommandMessage,
                  _: Dict=None) -> Union[str, UserContext]:
    if msg.text in hateb.allowed_categories:
        feed = hateb.retrieve_feed(msg.text)
        gist_url = hateb.post_gist(feed)

        # Multi-line message is folded by default, so entries are not spliced.
        list_string = '\n'.join(
            ['[%d] %s : %s' % (e.bookmark_count,
                               e.title,
                               e.link) for e in feed.entries])

        return '%s\n\n Detail: %s' % (list_string, gist_url)
    else:
        message = ("Please choose a category from below:\n%s" %
                   ", ".join(hateb.allowed_categories))
        return UserContext(message=message,
                           help_message=message,
                           input_options=(InputOption(".", slack_hateb),))
