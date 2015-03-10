# -*- coding: utf-8 -*-

# Copyright (c) 2014, KOL
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from urllib import urlencode
from datetime import date

PREFIX_V = '/video/vkontakte'
PREFIX_M = '/music/vkontakte'
PREFIX_P = '/photos/vkontakte'

ART = 'art-default.jpg'
ICON = 'icon-default.png'
TITLE = u'%s' % L('Title')

VK_APP_ID = 4510304
VK_APP_SECRET = 'H4uZCbIucFgmsHKprXla'
VK_APP_SCOPE = 'audio,video,groups,friends'
VK_VERSION = '5.24'
VK_LIMIT = 50


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
            header=u'%s' % L('Success'),
            message=u'%s' % L('Authorization complete')
        )
    else:
        return BadAuthMessage()


def ValidateAuth():
    return (Dict['token'] or
        (Prefs['username'] and Prefs['password'] and CheckToken())
    )


###############################################################################
# Video
###############################################################################

@handler(PREFIX_V, u'%s' % L('VideoTitle'), R(ART), R(ICON))
def VideoMainMenu():
    if not Dict['token']:
        return BadAuthMessage()

    oc = ObjectContainer(title2=TITLE, no_cache=True)
    oc.add(DirectoryObject(
        key=Callback(VideoListGroups, uid=Dict['user_id']),
        title=u'%s' % L('My groups')
    ))
    oc.add(DirectoryObject(
        key=Callback(VideoListFriends, uid=Dict['user_id']),
        title=u'%s' % L('My friends')
    ))

    oc.add(InputDirectoryObject(
        key=Callback(
            Search,
            search_type='video',
            title=u'%s' % L('Search Video')
        ),
        title=u'%s' % L('Search'), prompt=u'%s' % L('Search Video')
    ))

    return AddVideoAlbums(oc, Dict['user_id'])


@route(PREFIX_V + '/groups')
def VideoListGroups(uid, offset=0):
    return GetGroups(VideoAlbums, VideoListGroups, uid, offset);


@route(PREFIX_V + '/friends')
def VideoListFriends(uid, offset=0):
    return GetFriends(VideoAlbums, VideoListFriends, uid, offset)


@route(PREFIX_V + '/albums')
def VideoAlbums(uid, title, offset=0):
    oc = ObjectContainer(
        title2=u'%s' % title,
        replace_parent=(offset > 0)
    )
    return AddVideoAlbums(oc, uid, offset)


@route(PREFIX_V + '/list')
def VideoList(uid, title, album_id=None, offset=0):
    params = {
        'owner_id': uid,
        'width': 320,
        'count': Prefs['video_per_page'],
        'offset': offset
    }
    if album_id is not None:
        params['album_id'] = album_id

    res = ApiRequest('video.get', params)

    if not res or not res['count']:
        return NoContents()

    oc = ObjectContainer(
        title2=(u'%s' % title),
        content=ContainerContent.GenericVideos,
        replace_parent=(offset > 0)
    )

    for item in res['items']:
        try:
            vco = GetVideoObject(item)
            oc.add(vco)
        except Exception as e:
            try:
                Log.Warn('Can\'t add video to list: %s', e.status)
            except:
                continue

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
            title=u'%s' % L('Next page')
        ))

    return oc


@route(PREFIX_V + '/play')
def VideoPlay(uid, vid):

    res = ApiRequest('video.get', {
        'owner_id': uid,
        'videos': '%s_%s' % (uid, vid),
        'width': 320,
    })

    if not res or not res['count']:
        return NoContents()

    item = res['items'][0]

    if not item:
        raise Ex.MediaNotAvailable

    return ObjectContainer(
        objects=[GetVideoObject(item)],
        content=ContainerContent.GenericVideos
    )


def AddVideoAlbums(oc, uid, offset=0):
    albums = ApiRequest('video.getAlbums', {
        'owner_id': uid,
        'extended': 1,
        'count': VK_LIMIT,
        'offset': offset
    })

    has_albums = albums and albums['count']
    offset = int(offset)

    if not offset:
        if not has_albums and not len(oc.objects):
            return VideoList(uid=uid, title=u'%s' % L('All videos'))
        else:
            oc.add(DirectoryObject(
                key=Callback(
                    VideoList, uid=uid,
                    title=u'%s' % L('All videos'),
                ),
                title=u'%s' % L('All videos'),
            ))


    if has_albums:
        for item in albums['items']:
            # display playlist title and number of videos
            title = u'%s: %s (%d)' % (L('Album'), item['title'], item['count'])
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

        offset = offset+VK_LIMIT
        if offset < albums['count']:
            oc.add(NextPageObject(
                key=Callback(
                    VideoAlbums,
                    uid=uid,
                    title=oc.title2,
                    offset=offset
                ),
                title=u'%s' % L('More albums')
            ))

    return oc

def GetVideoObject(item):
    if 'external' in item['files']:
        return URLService.MetadataObjectForURL(
            NormalizeExternalUrl(item['files']['external'])
        )

    return VideoClipObject(
        key=Callback(
            VideoPlay,
            uid=item['owner_id'],
            vid=item['id']
        ),
        rating_key='%s.%s' % (Plugin.Identifier, item['id']),
        title=u'%s' % item['title'],
        source_title=TITLE,
        summary=item['description'],
        thumb=item['photo_320'],
        source_icon=R(ICON),
        originally_available_at=date.fromtimestamp(item['date']),
        duration=(item['duration']*1000),
        items=[
            MediaObject(
                parts=[PartObject(
                    key=item['files'][r]
                )],
                video_resolution=r.replace('mp4_', ''),
                container=Container.MP4,
                video_codec=VideoCodec.H264,
                audio_codec=AudioCodec.AAC,
                optimized_for_streaming=True
            ) for r in sorted(item['files'], reverse=True) if 'mp4_' in r
        ]
    )


###############################################################################
# Music
###############################################################################

@handler(PREFIX_M, u'%s' % L('MusicTitle'), R(ART), R(ICON))
def MusicMainMenu():
    if not Dict['token']:
        return BadAuthMessage()

    oc = ObjectContainer(title2=TITLE, no_cache=True)
    oc.add(DirectoryObject(
        key=Callback(MusicListGroups, uid=Dict['user_id']),
        title=u'%s' % L('My groups')
    ))
    oc.add(DirectoryObject(
        key=Callback(MusicListFriends, uid=Dict['user_id']),
        title=u'%s' % L('My friends')
    ))

    oc.add(InputDirectoryObject(
        key=Callback(
            Search,
            search_type='audio',
            title=u'%s' % L('Search Music')
        ),
        title=u'%s' % L('Search'), prompt=u'%s' % L('Search Music')
    ))

    return AddMusicAlbums(oc, Dict['user_id'])


@route(PREFIX_M + '/groups')
def MusicListGroups(uid, offset=0):
    return GetGroups(MusicAlbums, MusicListGroups, uid, offset)


@route(PREFIX_M + '/friends')
def MusicListFriends(uid, offset=0):
    return GetFriends(MusicAlbums, MusicListFriends, uid, offset)


@route(PREFIX_M + '/albums')
def MusicAlbums(uid, title, offset=0):
    oc = ObjectContainer(
        title2=u'%s' % title,
        replace_parent=(offset > 0)
    )
    return AddMusicAlbums(oc, uid, offset)


@route(PREFIX_M + '/list')
def MusicList(uid, title, album_id=None, offset=0):

    params = {
        'owner_id': uid,
        'count': Prefs['audio_per_page'],
        'offset': offset
    }
    if album_id is not None:
        params['album_id'] = album_id

    res = ApiRequest('audio.get', params)

    if not res or not res['count']:
        return NoContents()

    oc = ObjectContainer(
        title2=(u'%s' % title),
        content=ContainerContent.Tracks,
        replace_parent=(offset > 0)
    )

    for item in res['items']:
        oc.add(GetTrackObject(item))

    offset = int(offset)+VK_LIMIT
    if offset < res['count']:
        oc.add(NextPageObject(
            key=Callback(
                MusicList,
                uid=uid,
                title=title,
                album_id=album_id,
                offset=offset
            ),
            title=u'%s' % L('Next page')
        ))

    return oc


@route(PREFIX_M + '/play')
def MusicPlay(info):

    item = JSON.ObjectFromString(info)

    if not item:
        raise Ex.MediaNotAvailable

    return ObjectContainer(
        objects=[GetTrackObject(item)],
        content=ContainerContent.Tracks
    )


def AddMusicAlbums(oc, uid, offset=0):

    albums = ApiRequest('audio.getAlbums', {
        'owner_id': uid,
        'count': VK_LIMIT,
        'offset': offset
    })

    has_albums = albums and albums['count']
    offset = int(offset)

    if not offset:
        if not has_albums and not len(oc.objects):
            return MusicList(uid=uid, title=u'%s' % L('All tracks'))
        else:
            oc.add(DirectoryObject(
                key=Callback(
                    MusicList, uid=uid,
                    title=u'%s' % L('All tracks'),
                ),
                title=u'%s' % L('All tracks'),
            ))

    if has_albums:
        for item in albums['items']:
            # display playlist title and number of videos
            title = u'%s: %s' % (L('Album'), item['title'])

            oc.add(DirectoryObject(
                key=Callback(
                    MusicList, uid=uid,
                    title=u'%s' % item['title'],
                    album_id=item['id']
                ),
                title=title,
            ))

        offset = offset+VK_LIMIT
        if offset < albums['count']:
            oc.add(NextPageObject(
                key=Callback(
                    MusicAlbums,
                    uid=uid,
                    title=oc.title2,
                    offset=offset
                ),
                title=u'%s' % L('More albums')
            ))

    return oc


def GetTrackObject(item):
    return TrackObject(
        key=Callback(MusicPlay, info=JSON.StringFromObject(item)),
        # rating_key='%s.%s' % (Plugin.Identifier, item['id']),
        # Rating key must be integer because PHT and PlexConnect
        # does not support playing queue with string rating key
        rating_key=item['id'],
        title=u'%s' % item['title'],
        artist=u'%s' % item['artist'],
        duration=int(item['duration'])*1000,
        items=[
            MediaObject(
                parts=[PartObject(key=item['url'])],
                container=Container.MP3,
                audio_codec=AudioCodec.MP3,
                audio_channels=2,
                video_codec='',  # Crutch for disable generate parts,
                optimized_for_streaming=True,
            )
        ]
    )


###############################################################################
# Photos
###############################################################################

@handler(PREFIX_P, u'%s' % L('PhotosTitle'), R(ART), R(ICON))
def PhotoMainMenu():
    if not Dict['token']:
        return BadAuthMessage()

    oc = ObjectContainer(title2=TITLE, no_cache=True)
    oc.add(DirectoryObject(
        key=Callback(PhotoListGroups, uid=Dict['user_id']),
        title=u'%s' % L('My groups')
    ))
    oc.add(DirectoryObject(
        key=Callback(PhotoListFriends, uid=Dict['user_id']),
        title=u'%s' % L('My friends')
    ))

    return AddPhotoAlbums(oc, Dict['user_id'])


@route(PREFIX_P + '/groups')
def PhotoListGroups(uid, offset=0):
    return GetGroups(PhotoAlbums, PhotoListGroups, uid, offset)


@route(PREFIX_P + '/friends')
def PhotoListFriends(uid, offset=0):
    return GetFriends(PhotoAlbums, PhotoListFriends, uid, offset)


@route(PREFIX_P + '/albums')
def PhotoAlbums(uid, title, offset=0):
    oc = ObjectContainer(title2=u'%s' % title, replace_parent=(offset > 0))
    return AddPhotoAlbums(oc, uid, offset)


@route(PREFIX_P + '/list')
def PhotoList(uid, title, album_id, offset=0):
    res = ApiRequest('photos.get', {
        'owner_id': uid,
        'album_id': album_id,
        'extended': 0,
        'photo_sizes': 1,
        'rev': 1,
        'count': Prefs['photos_per_page'],
        'offset': offset
    })

    if not res or not res['count']:
        return NoContents()

    oc = ObjectContainer(
        title2=(u'%s' % title),
        content='photo',
        replace_parent=(offset > 0)
    )

    for item in res['items']:
        oc.add(GetPhotoObject(item))

    offset = int(offset)+VK_LIMIT
    if offset < res['count']:
        oc.add(NextPageObject(
            key=Callback(
                PhotoList,
                uid=uid,
                title=title,
                album_id=album_id,
                offset=offset
            ),
            title=u'%s' % L('Next page')
        ))

    return oc


def AddPhotoAlbums(oc, uid, offset=0):

    albums = ApiRequest('photos.getAlbums', {
        'owner_id': uid,
        'need_covers': 1,
        'photo_sizes': 1,
        'need_system': 1,
        'count': VK_LIMIT,
        'offset': offset
    })

    has_albums = albums and albums['count']
    offset = int(offset)

    if has_albums:
        for item in albums['items']:
            thumb = ''
            for size in item['sizes']:
                if size['type'] == 'p':
                    thumb = size['src']
                    break

            oc.add(DirectoryObject(
                key=Callback(
                    PhotoList, uid=uid,
                    title=u'%s' % item['title'],
                    album_id=item['id']
                ),
                summary=item['description'] if 'description' in item else '',
                title=u'%s (%s)' % (item['title'], item['size']),
                thumb=thumb,
            ))

        offset = offset+VK_LIMIT
        if offset < albums['count']:
            oc.add(NextPageObject(
                key=Callback(
                    PhotoAlbums,
                    uid=uid,
                    title=oc.title2,
                    offset=offset
                ),
                title=u'%s' % L('More albums')
            ))

    if not len(oc.objects):
        return NoContents()

    return oc


def GetPhotoObject(item):

    sizes = {}
    for size in item['sizes']:
        sizes[size['type']] = size['src']

    url = ''
    for size in ['z', 'y', 'x']:
        if size in sizes:
            url = sizes[size]
            break

    return PhotoObject(
        key=url,
        rating_key='%s.%s' % (Plugin.Identifier, item['id']),
        summary=u'%s' % item['text'],
        thumb=sizes['p'] if 'p' in sizes else ''
    )


###############################################################################
# Common
###############################################################################

def Search(query, title=u'%s' % L('Search'), search_type='video', offset=0):

    is_video = search_type == 'video'

    params = {
        'sort': 2,
        'offset': offset,
        'count': Prefs[search_type + '_per_page'],
        'q': query
    }

    if is_video:
        if Prefs['search_hd']:
            params['hd'] = 1
        if Prefs['search_adult']:
            params['adult'] = 1

    res = ApiRequest(search_type+'.search', params)

    if not res or not res['count']:
        return NoContents()

    oc = ObjectContainer(
        title2=(u'%s' % title),
        replace_parent=(offset > 0),
    )

    if is_video:
        method = GetVideoObject
        oc.content = ContainerContent.GenericVideos
    else:
        method = GetTrackObject
        oc.content = ContainerContent.Tracks

    for item in res['items']:
        oc.add(method(item))

    offset = int(offset)+VK_LIMIT
    if offset < res['count']:
        oc.add(NextPageObject(
            key=Callback(
                Search,
                query=query,
                title=title,
                search_type=search_type,
                offset=offset
            ),
            title=u'%s' % L('Next page')
        ))

    return oc


def BadAuthMessage():
    return MessageContainer(
        header=u'%s' % L('Error'),
        message=u'%s' % L('NotAuth')
    )


def NoContents():
    return ObjectContainer(
        header=u'%s' % L('Error'),
        message=u'%s' % L('No entries found')
    )


def NormalizeExternalUrl(url):
    # Rutube service crutch
    if Regex('//rutube.ru/[^/]+/embed/[0-9]+').search(url):
        url = HTML.ElementFromURL(url, cacheTime=CACHE_1WEEK).xpath(
            '//link[contains(@rel, "canonical")]'
        )
        if url:
            return url[0].get('href')

    return url


def GetGroups(callback_action, callback_page, uid, offset):
    '''Get groups container with custom callback'''
    oc = ObjectContainer(
        title2=u'%s' % L('My groups'),
        replace_parent=(offset > 0)
    )
    groups = ApiRequest('groups.get', {
        'user_id': uid,
        'extended': 1,
        'count': VK_LIMIT,
        'offset': offset
    })
    if groups and groups['count']:
        for item in groups['items']:
            title = u'%s' % item['name']
            if 'photo_200' in item:
                thumb = item['photo_200']
            else:
                thumb = R(ICON)

            oc.add(DirectoryObject(
                key=Callback(
                    callback_action,
                    uid=(item['id']*-1),
                    title=title,
                ),
                title=title,
                thumb=thumb
            ))

        offset = int(offset)+VK_LIMIT
        if offset < groups['count']:
            oc.add(NextPageObject(
                key=Callback(
                    callback_page,
                    uid=uid,
                    offset=offset
                ),
                title=u'%s' % L('More groups')
            ))

    return oc


def GetFriends(callback_action, callback_page, uid, offset):
    '''Get friends container with custom callback'''
    oc = ObjectContainer(
        title2=u'%s' % L('My friends'),
        replace_parent=(offset > 0)
    )
    friends = ApiRequest('friends.get', {
        'user_id': uid,
        'fields': 'photo_200_orig',
        'order': 'hints',
        'count': VK_LIMIT,
        'offset': offset
    })
    if friends and friends['count']:
        for item in friends['items']:
            title = u'%s %s' % (item['first_name'], item['last_name'])
            if 'photo_200_orig' in item:
                thumb = item['photo_200_orig']
            else:
                thumb = R(ICON)

            oc.add(DirectoryObject(
                key=Callback(
                    callback_action,
                    uid=item['id'],
                    title=title,
                ),
                title=title,
                thumb=thumb
            ))

        offset = int(offset)+VK_LIMIT
        if offset < friends['count']:
            oc.add(NextPageObject(
                key=Callback(
                    callback_page,
                    uid=uid,
                    offset=offset
                ),
                title=u'%s' % L('Next page')
            ))

    return oc


def ApiRequest(method, params):
    params['access_token'] = Dict['token']
    params['v'] = VK_VERSION
    res = JSON.ObjectFromURL(
        'https://api.vk.com/method/%s?%s' % (method, urlencode(params)),
    )

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

    if res and ('access_token' in res):
        Dict['token'] = res['access_token']
        Dict['user_id'] = res['user_id']
        Dict.Save()
        return True

    return False
