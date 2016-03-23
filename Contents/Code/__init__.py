import urllib, ssl
from socket import timeout

####################################################################################################
PREFIX = "/video/letmestream"
NAME = "LetMeStream"
ICON     = 'icon_default.png'
####################################################################################################

lmsToken = Prefs['lmstoken']
collTvShows = {}
collMovies = {}
sessionsCalled = {}

def Start():
    ObjectContainer.title1 = NAME
@handler(PREFIX, NAME)
def MainMenu():
    if not Prefs['lmstoken']:
        return ObjectContainer(header=L('Not configured'), message=L('No LetMeStream token configured.'))
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(TvShows), title=L("TvShows"), thumb=R('tvshows.png')))
    oc.add(DirectoryObject(key=Callback(Movies), title=L("Movies"), thumb=R('Movies.png')))
    return oc

def setItem(key, value):
    return Data.SaveObject('lms' + str(key), value)

def getItem(key):
    if Data.Exists('lms' + str(key)):
        return Data.LoadObject('lms' + str(key))
    return None

def ValidatePrefs():
    return True

@route(PREFIX + '/TvShow', itemId = int)
def GetTvShow(itemId):
    oc = ObjectContainer()
    item = getItem(itemId)
    if not item:
        raise Ex.MediaNotAvailable

    oc.title1 = item['title']
    ObjectContainer.art = Callback(Thumb, url=item['backdrop'])

    url = 'http://cdn.letmestream.com/api/plex/episodes/' + str(item['mediaParentId']) + '?token=' + lmsToken
    content = HTTP.Request(url, cacheTime = CACHE_1DAY).content
    seasons = JSON.ObjectFromString(content)['seasons']
    item['seasons'] = seasons
    collTvShows[str(item['id'])] = item
    setItem(item['id'], item)
    for season in seasons:
        if season['season'] > 0:
            oc.add(SeasonObject(show=item['title'], episode_count=len(season['episodes']), key=Callback(TvShowSeason, itemId = item['id'], seasonInt = season['season']), rating_key=str(item['id']) + '-' + str(season['season']), title="Season " + str(season['season']), thumb=Callback(Thumb, url=item['poster'] + '?' + str(season['season']))))
    return oc

@route(PREFIX + '/TvShow/season', itemId = int, seasonInt = int)
def TvShowSeason(itemId, seasonInt):
    oc = ObjectContainer()
    item = getItem(itemId)
    oc.title1 = item['title'] + ' - Season ' + str(seasonInt)
    ObjectContainer.art = Callback(Thumb, url=item['backdrop'])
    fullIndex = 0
    for season in item['seasons']:
        if season['season'] == seasonInt:
            episodes = season['episodes']
            for episode in episodes:
                fullIndex = fullIndex + 1
                episode =  JSON.ObjectFromString(episode)
                episode = episodes[str(episode)]
                Log(episode)
                episode['backdrop'] = item['backdrop']
                episode['type'] = 'episode'
                episode['poster'] = episode['thumb']
                episode['title'] = episode['key'] + ' - ' + (episode['title'].replace(episode['key'] + ' - ', ''))
                openSubtitlesHash = None
                try:
                    if episode['subtitlesHash'] and len(episode['subtitlesHash']) > 0:
                        openSubtitlesHash = episode['subtitlesHash'][0]
                except:
                    pass
                setItem(episode['id'], episode)
                epdObject = EpisodeObject(key=Callback(videoClipFromItem, itemId = episode['id'], include_container = True),  season = episode['season'], absolute_index = fullIndex, rating_key=episode['title'], title=episode['title'], art=Callback(Thumb, url = item['backdrop']), thumb=Callback(Thumb, url = episode['poster'], failback = item['poster']), summary = episode['overview'])
                epdObject.show = item['title']
                epdObject.season = seasonInt
                epdObject.absolute_index = fullIndex
                epdObject.source_title = 'LetMeStream'
                oc.add(epdObject)
            break
        else:
            fullIndex = fullIndex + len(season['episodes'])
    return oc

@route(PREFIX + '/TvShows')
def TvShows(oc = None):
    oc = ObjectContainer()
    oc.title1 = L('TvShows')
    i = 0
    items = []
    collTvShows = {}
    start = 0
    end = 14
    while i < 100:
        items = getItems('genretvshowall', start, end)
        for item in items:
            try:
                if not item['id'] or collTvShows[str(item['id'])] or not item['title']:
                    continue
            except:
                pass
            item['type'] = 'show'
            collTvShows[str(item['id'])] = item
            setItem(item['id'], item)
            try:
                itemKey = item['title'] + '#' + str(item['id'])
                oc.add(TVShowObject(key=Callback(GetTvShow, itemId = item['id']), rating_key=itemKey, title=item['title'], art=Callback(Thumb, url = item['backdrop']), thumb=Callback(Thumb, url = item['poster'])))
            except:
                pass
        if len(items) < 1:
            break
        start += len(items)
        i += 1
    return oc

@route(PREFIX + '/lmsMovies')
def Movies(oc = None):
    oc = ObjectContainer()
    oc.title1 = L('Movies')
    i = 0
    items = []
    start = 0
    end = 14
    collMovies = {}
    while i < 100:
        items = getItems('genreall', start, end)
        for item in items:
            try:
                if not item['id'] or collMovies[str(item['id'])] or not item['title']:
                    continue
            except:
                pass
            item['type'] = 'movie'
            collMovies[str(item['id'])] = item
            setItem(item['id'], item)
            try:
                oc.add(MovieObject(key=Callback(videoClipFromItem, itemId = item['id'], include_container = True), rating_key=item['title'], title=item['title'], art=Callback(Thumb, url = item['backdrop']), thumb=Callback(Thumb, url = item['poster'])))
            except:
                pass

        if len(items) < 1:
            break
        start += len(items)
        i += 1
    return oc

def getUrl(item):
    itemUrl = 'lms://' + str(item['locationsInfos'][0]['id']) + ':' + Prefs['lmstoken'] + ':0:' + Prefs['subtitlesLanguage']
    try:
        return itemUrl
    except:
        return None

@route(PREFIX + '/thumb', url = str)
def Thumb(url, failback = None):
  try:
    url = url.replace('https://', 'http://')
    data = HTTP.Request(url, cacheTime = CACHE_1MONTH).content
    return DataObject(data, 'image/jpeg')
  except:
    if failback:
        return Redirect(failback)

    return Redirect(R(ICON))

@route(PREFIX + '/media/videoclip', itemId = int)
def videoClipFromItem(itemId, include_container = False, includeRelated = False, includeRelatedCount = False, includeExtras = False):
    item = getItem(itemId)
    return CreateVideoClipObject(
        itemType = item['type'],
        item = item,
        url = getUrl(item),
        title = item['title'],
        summary = item['overview'],
        thumb = item['poster'],
        backdrop = item['backdrop'],
        mediaLocationId = item['mediaLocationId'],
        mediaItemId = item['mediaItemId'],
        mediaFileId = item['mediaFileId'],
        include_container = include_container,
        includeRelated = includeRelated,
        includeExtras = includeExtras
    )

def CreateVideoClipObject(itemType, item, url, title, summary, thumb, backdrop, mediaLocationId, mediaItemId, mediaFileId, include_container, includeRelated, includeExtras):
    videoContainer = 'mp4'
    videoCodec = VideoCodec.H264
    videoResolution = '544'
    audioCodec = AudioCodec.AAC
    optimizedForStreaming = 1
    videoHeight = 1
    videoWidth = 1
    duration = 0
    videoProtocol = 'HTTPMP4Video'

    classmap = {
        'generic': VideoClipObject,
        'movie': MovieObject,
        'episode':  EpisodeObject,
        'show': TVShowObject,
        'season': SeasonObject
    }
    if itemType == 'episode' and not include_container:
        videoclip_obj = VideoClipObject(
            url =  url,
            rating_key = url,
            title = title,
            art = Callback(Thumb, url=backdrop),
            thumb =  Callback(Thumb, url=thumb)
        )
    else :
        videoclip_obj = classmap[itemType](
            url =  url,
            rating_key = url,
            title = title,
            art = Callback(Thumb, url=backdrop),
            thumb =  Callback(Thumb, url=thumb),
            summary = summary

        )
    if include_container:
		return ObjectContainer(objects=[videoclip_obj])
    else:
		return videoclip_obj

def getItems(itemsType, start=0, end=14):
    try:
        if not start:
            start = str(0)
        url = 'http://cdn.letmestream.com/api/plex/frontParse/' + itemsType + '/' + str(start) + ',' + str(int(end)) + '?token=' + lmsToken
        items = JSON.ObjectFromString(HTTP.Request(url, cacheTime = CACHE_1DAY).content)['items']
        return items
    except:
        return []