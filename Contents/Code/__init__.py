# -*- coding: utf-8 -*-

from urllib import urlencode
from datetime import date

PREFIX_V = '/video/vkontakte'
PREFIX_M = '/music/vkontakte'

# make sure to replace artwork with what you want
# these filenames reference the example files in
# the Contents/Resources/ folder in the bundle
ART = 'art-default.jpg'
ICON = 'icon-default.png'

VK_APP_ID = 4510304
VK_APP_SECRET = 'H4uZCbIucFgmsHKprXla'
VK_APP_SCOPE = 'audio,video,groups,friends'
VK_VERSION = '5.24'
VK_LIMIT = 5


###############################################################################
# Init
###############################################################################

def Start():

    HTTP.CacheTime = CACHE_1HOUR
    ValidateAuth()


def ValidatePrefs():
    Dict.Reset()

    if (ValidateAuth()):
        return MessageContainer(
            L('Success'),
            L('Authorization complete')
        )
    else:
        return MessageContainer(
            L('Error'),
            GetBadAuthMessage()
        )


def ValidateAuth():
    return (Dict['token'] or (Prefs['username'] and Prefs['password'] and CheckToken()))


def GetBadAuthMessage():
    return L('You must specify correct username and password in preferences')


###############################################################################
# Video
###############################################################################

@handler(PREFIX_V, L('VideoTitle'), R(ART), R(ICON))
def VideoMainMenu():
    if not Dict['token']:
        return ObjectContainer(header=L('Error'), message=GetBadAuthMessage())

    oc = ObjectContainer(title2=L('VideoTitle'), no_cache=True)
    oc.add(DirectoryObject(
        key=Callback(ListGroups, title=L('My groups')),
        title=L('My groups')
    ))
    oc.add(DirectoryObject(
        key=Callback(ListFriends, title=L('My friends')),
        title=L('My friends')
    ))

    oc.add(DirectoryObject(
        key=Callback(VideoList, uid=Dict['user_id'], title=L('My videos')),
        title=L('My videos')
    ))

    return AddVideoAlbums(oc, Dict['user_id'])


@route(PREFIX_V + '/groups')
def ListGroups():
    return Notimplemented()


@route(PREFIX_V + '/friends')
def ListFriends():
    return Notimplemented()


@route(PREFIX_V + '/albums')
def VideoAlbums(uid, title, offset):
    oc = ObjectContainer(title2=title, replace_parent=(offset>0))
    return AddVideoAlbums(oc, uid, offset)


def AddVideoAlbums(oc, uid, offset=0):

    # Fill albums first
    albums = ApiRequest('video.getAlbums', {
        'owner_id': uid,
        'extended': 1,
        'count': VK_LIMIT,
        'offset': offset
    })

    if albums and albums['count'] and len(albums['items']) > 0:
        for item in albums['items']:
            videos = item['count']
            #display playlist title and number of videos
            title = u'%s: %s (%d videos)' % (L('Album'), item['title'], videos)
            if 'photo_320' in item:
                thumb = item['photo_320']
            else:
                thumb = R(ICON)

            oc.add(DirectoryObject(
                key=Callback(
                    VideoList, uid=uid,
                    title=u'%s' % item['title'],
                    album_id=item['id']
                ),
                title=title,
                thumb=thumb
            ))

        offset = int(offset)+VK_LIMIT
        if offset < albums['count']:
            oc.add(NextPageObject(
                key=Callback(
                    VideoAlbums,
                    uid=uid,
                    title=oc.title2,
                    offset=offset
                ),
                title=L('More albums')
            ))

    return oc


@route(PREFIX_V + '/list')
def VideoList(uid, title, album_id=0, offset=0):
    res = ApiRequest('video.get', {
        'owner_id': uid,
        'album_id': album_id,
        'width': 320,
        'count': VK_LIMIT,
        'offset': offset
    })

    if not res or not res['count']:
        return ObjectContainer(
            header=L('Error'),
            message=L('This feed does not contain any entries')
        )

    oc = ObjectContainer(title2=(u'%s' % title), replace_parent=(offset > 0))

    for item in res['items']:
        # External flash player
        oc.add(VideoClipObject(
            key=Callback(VideoView, info=JSON.StringFromObject(item)),
            rating_key=item['player'],
            title=u'%s' % item['title'],
            summary=item['description'],
            thumb=item['photo_320'],
            originally_available_at=date.fromtimestamp(item['date']),
            duration=(item['duration']*1000),
        ))

    offset = int(offset)+VK_LIMIT
    if offset < res['count']:
        oc.add(NextPageObject(
            key=Callback(
                VideoList,
                uid=uid,
                title=title,
                album_id=album_id,
                offset=offset
            ),
            title=L('Next page')
        ))

    return oc


@route(PREFIX_V + '/video/view')
def VideoView(info, include_container=True):

    item = JSON.ObjectFromString(info)
    files = sorted(item['files'], reverse=True)
    thumb = item['photo_130']

    if include_container:
        thumb = item['photo_320']

    if 'external' in item['files']:
        vco = VideoClipObject(
            url=NormalizeExternalUrl(item['files']['external']),
            title=u'%s' % item['title'],
            summary=item['description'],
            thumb=thumb,
            originally_available_at=date.fromtimestamp(item['date']),
            duration=(item['duration']*1000)
        )
        Log.Debug('External url: %s' % vco.url)
    else:
        vco = VideoClipObject(
            key=Callback(VideoView, info=info, include_container=False),
            rating_key=item['player'],
            title=u'%s' % item['title'],
            summary=item['description'],
            thumb=thumb,
            originally_available_at=date.fromtimestamp(item['date']),
            duration=(item['duration']*1000),
            items=[
                MediaObject(
                    parts=[PartObject(key=Callback(
                        PlayVideo,
                        url=item['files'][resolution],
                        post_url=item['player']
                    ))],
                    video_resolution=resolution.replace('mp4_', ''),
                    container=Container.MP4,
                    video_codec=VideoCodec.H264,
                    audio_codec=AudioCodec.AAC,
                    audio_channels=2,
                    optimized_for_streaming=True
                ) for resolution in files
            ]
        )

    if (include_container):
        return ObjectContainer(title2=vco.title, objects=[vco])

    return vco


@route(PREFIX_V + '/video/play')
@indirect
def PlayVideo(url=None, **kwargs):
    if not url:
        return None

    return IndirectResponse(VideoClipObject, key=url)


def NormalizeExternalUrl(url):
    if Regex('//rutube.ru/[^/]+/embed/[0-9]+').search(url):
        url = HTML.ElementFromURL(url).xpath(
            '//link[contains(@rel, "canonical")]'
        )
        if url:
            return url[0].get('href')

    return url


###############################################################################
# Music
###############################################################################
@handler(PREFIX_M, L('MusicTitle'), R(ART), R(ICON))
def MusicMainMenu():
    if not Dict['token']:
        return ObjectContainer(header=L('Error'), message=GetBadAuthMessage())

    oc = ObjectContainer(title2=L('MusicTitle'), no_cache=True)
    oc.add(DirectoryObject(
        key=Callback(ListGroups, title=L('My groups')),
        title=L('My groups')
    ))


def SearchResults(sender, query=None):
    return Notimplemented()


def Notimplemented():
    return MessageContainer(
        L('Not implemented'),
        L('In real life, you would probably perform some search using ' +
            'python\nand then build a MediaContainer with items\nfor ' +
            'the results')
    )


def ApiRequest(method, params):
    params['access_token'] = Dict['token']
    params['v'] = VK_VERSION
    res = JSON.ObjectFromURL(
        'https://api.vk.com/method/%s?%s' % (method, urlencode(params)),
        cacheTime=1
    )
    Log.Debug(res)
    if res and ('response' in res):
        return res['response']

    return False


def CheckToken():
    url = 'https://oauth.vk.com/token?' + urlencode({
        'grant_type': 'password',
        'client_id': VK_APP_ID,
        'client_secret': VK_APP_SECRET,
        'username': Prefs['username'],
        'password': Prefs['password'],
        'scope': VK_APP_SCOPE,
        'v': VK_VERSION
    })
    res = JSON.ObjectFromURL(url)

    Log.Debug(res)

    if res and ('access_token' in res):
        Dict['token'] = res['access_token']
        Dict['user_id'] = res['user_id']
        Dict.Save()
        return True

    return False
