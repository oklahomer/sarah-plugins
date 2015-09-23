# -*- coding: utf-8 -*-
import logging
import flickrapi
from sarah.bot.slack import Slack, MessageAttachment, SlackMessage
from typing import Dict, Optional


@Slack.schedule('flickr_interesting_photos')
def interesting_pictures(config: Dict) -> Optional[SlackMessage]:
    # Setup client module
    flickr = flickrapi.FlickrAPI(config['api_key'],
                                 config['api_secret'],
                                 format="parsed-json")
    # Retrieve top interesting photos
    try:
        response = flickr.interestingness_getList()
        # parsed = json.loads(response.decode('utf-8'))
        if response['stat'] != "ok":
            raise Exception("API status error")

        photos = response['photos']['photo'][:20]
    except KeyError as e:
        logging.error("API Response format error. %s." % e)
        return
    except Exception as e:
        logging.error("API Response error. %s", e)
        return
    else:
        if not photos:
            return

    # Retrieve location information for each photo
    # I want some sort of "bulk" API like the one Facebook has...
    attachments = []
    for p in photos:
        location_url = None
        location_name = None
        try:
            # https://gist.github.com/anonymous/1861a9dcc96848848cbf
            # geo_response = flickr.do_flickr_call(
            #     "flickr.photos.geo.getLocation",
            #     photo_id=p['id'])
            geo_response = flickr.photos_geo_getLocation(photo_id=p['id'])
            if geo_response['stat'] != "ok":
                # Skip if no location is registered.
                # {"stat":"fail",
                #  "code":2,
                #  "message": "Photo has no location information."}
                raise Exception(geo_response.get('message',
                                                 "API Response error."))

            location = geo_response['photo']['location']
            lat = location['latitude']
            lon = location['longitude']
            # accuracy = location['accuracy']
        except KeyError as e:
            logging.error("Error on retrieving photo location. %s" % e)
        except Exception as e:
            logging.error("Location API Error: %s", e)
        else:
            # If stringified location fragments are provided, construct a name
            # from them.
            location_name = ", ".join(
                filter(None,
                       [location.get(k, {}).get('_content', None) for k
                        in ['locality', 'county', 'region', 'country']]))
            if not location_name:
                location_name = ", ".join([lat, lon])

            location_url = "https://www.flickr.com/map/" \
                           "?fLat=%s&fLon=%s&zl=13&everyone_nearby=1" % (lat,
                                                                         lon)

        attachments.append(MessageAttachment(
            fallback=p['title'],
            title=p['title'],
            title_link="https://www.flickr.com/photos/%s/%s" % (p['owner'],
                                                                p['id']),
            thumb_url="https://farm%s.staticflickr.com/%s/%s_%s_m.jpg" % (
                p['farm'], p['server'], p['id'], p['secret']
            ),
            author_link=location_url,
            author_name=location_name
        ))

    if attachments:
        return SlackMessage(text="\"Interesting\" photos on Flickr",
                            attachments=attachments)
