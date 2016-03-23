import urllib, ssl
from socket import timeout

def ceiling(no):
    try:
        return int(no)
    except:
        Log(no)

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
    #Plugin.AddViewGroup("Details", viewMode="InfoList", mediaType="items")
    #Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(TvShows, start = 0, end = 14), title=L("TvShows"), thumb=R('tvshows.png')))
    oc.add(DirectoryObject(key=Callback(Movies, start = 0, end = 14), title=L("Movies"), thumb=R('Movies.png')))
    return oc

def setVar(key, value):
    return Data.Save(key, value)

def getVar(key):
    if Data.Exists(key):
        return Data.Load(key)
    return None

def setItem(key, value):
    return Data.SaveObject(key, value)

def getItem(key):
    if Data.Exists(key):
        return Data.LoadObject(key)
    return None

def getItemTvShow(itemId):
    try:
        item = collTvShows[str(itemId)];
        if item:
            setItem('tvShow-' + str(itemId), item)
        else:
            item = getItem('tvShow-' + str(itemId))
        return item
    except:
        cached = getItem('tvShow-' + str(itemId))
        if cached:
            return cached

    return None

def getItemMovie(itemId):
    try:
        item = collMovies[str(itemId)];
        setItem('movie-' + str(itemId), item)
        return item
    except:
        cached = getItem('movie-' + str(itemId))
        if cached:
            return cached

    return None

def ValidatePrefs():
    return True

@route(PREFIX + '/TvShow', itemId = int)
def GetTvShow(itemId, item):
    oc = ObjectContainer()
    item = getItemTvShow(str(itemId))
    if not item:
        raise Ex.MediaNotAvailable

    oc.title1 = item['title']
    ObjectContainer.art = Callback(Thumb, url=item['backdrop'])

    url = 'http://cdn.letmestream.com/api/plex/episodes/' + str(item['mediaParentId']) + '?token=' + lmsToken
    content = HTTP.Request(url, cacheTime = CACHE_1DAY).content
    seasons = JSON.ObjectFromString(content)['seasons']
    item['seasons'] = seasons
    collTvShows[str(item['id'])] = item
    item = getItemTvShow(itemId)
    items = []
    for season in seasons:
        if season['season'] > 0:
            oc.add(SeasonObject(show=item['title'], episode_count=len(season['episodes']), key=Callback(TvShowSeason, itemId = item['id'], seasonInt = season['season']), rating_key=str(item['id']) + '-' + str(season['season']), title="Season " + str(season['season']), thumb=Callback(Thumb, url=item['poster'] + '?' + str(season['season']))))
    return oc

@route(PREFIX + '/TvShow/season', itemId = int, seasonInt = int)
def TvShowSeason(itemId, seasonInt):
    oc = ObjectContainer()
    item = getItemTvShow(itemId)
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

                epdObject = EpisodeObject(key=Callback(videoClipFromItem, item = episode, include_container = True),  season = episode['season'], absolute_index = fullIndex, rating_key=episode['title'], title=episode['title'], art=Callback(Thumb, url = item['backdrop']), thumb=Callback(Thumb, url = episode['poster'], failback = item['poster']))
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
def TvShows(oc = None, start = 0, end = 14):
    oc = ObjectContainer()
    oc.title1 = L('TvShows')
    i = 0
    items = []
    while i < 100:
        nitems = getItems('genretvshowall', len(items), int(end))
        items = items + nitems
        if len(nitems) < int(end) * i:
            break
        i = i + 1
    collTvShows = {}
    for item in items:
        try:
            if collTvShows[str(item['id'])] or not item['title'] or not item['id']:
                continue
        except:
            pass
        item['type'] = 'show'

        collTvShows[str(item['id'])] = item
        setItem('tvShow-' + str(item['id']), item)
        try:
            itemKey = item['title'] + '#' + str(item['id'])
            oc.add(TVShowObject(key=Callback(GetTvShow, itemId = item['id'], item = item), rating_key=itemKey, title=item['title'], art=Callback(Thumb, url = item['backdrop']), thumb=Callback(Thumb, url = item['poster'])))
        except:
            pass

    return oc

@route(PREFIX + '/lmsMovies')
def Movies(oc = None, start =0, end = 14):
    oc = ObjectContainer()
    oc.title1 = L('Movies')
    i = 0
    items = []
    while i < 100:
        nitems = getItems('genreall', len(items), int(end))
        items = items + nitems
        if len(nitems) < int(end) * i:
            break
        i = i + 1
    collMovies = {}
    for item in items:
        try:
            if collMovies[str(item['id'])]:
                continue
        except:
            pass
        item['type'] = 'movie'
        collMovies[str(item['id'])] = item
        getItemMovie(item['id'])
        try:
            oc.add(MovieObject(key=Callback(videoClipFromItem, item = item, include_container = True), rating_key=item['title'], title=item['title'], art=Callback(Thumb, url = item['backdrop']), thumb=Callback(Thumb, url = item['poster'])))
        except:
            pass

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

def createSession(mediaLocationId, force = False):
    if force:
        ext = 'm3u8'
    else:
        ext = 'mkv'

    url = 'http://cdn.letmestream.com/api/sessions/stream/' + str(mediaLocationId) + '.' + ext + '?fromPlex=1&ext=' + ext + '&token=' + lmsToken
    if(force == 2):
        data = None
        while not data:
            try:
                data = urllib.urlopen(url).read()
            except:
                return Callback(createSession, mediaLocationId = mediaLocationId, force = force)
        return data
    return url

    if not force:
        setVar('sessionable-' + str(mediaLocationId), True)
        return url

    return url

    url = 'http://cdn.letmestream.com/api/sessions/create/' + str(mediaLocationId) + '?token=' + lmsToken
    try:
        r = HTTP.Request(url)
        c = r.content
        sessionInfos = JSON.ObjectFromString(c)
    except:
        Log('Unable to create session'  )

    Log(sessionInfos)
    return sessionInfos['sessionUrl']

@route(PREFIX + '/data/cache', cacheKey = str)
def cache(cacheKey, data = None):
    try:
        return data
    except:
        return None

@route(PREFIX + '/media/analyze', mediaLocationId = int, mediaItemId = int, mediaFileId = int)
def analyzeItem(mediaLocationId, mediaItemId, mediaFileId):
    ObjectContainer(header=L('Empty'), message=L('Analyzing media...'))
    url = 'http://cdn.letmestream.com/api/media/analyze?locationId=' + str(mediaLocationId) + '&token=' + lmsToken
    try:
        analyzeInfos = JSON.ObjectFromString(HTTP.Request(url, cacheTime = CACHE_1HOUR).content)
        return analyzeInfos
    except:
        return None


def videoClipFromItem(item,  include_container = False, includeRelated = False, includeRelatedCount = False, includeExtras = False):
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
    #if True:
        #codecInfos = analyzeItem(mediaLocationId, mediaItemId, mediaFileId)
        #if not codecInfos:
        #    return ObjectContainer(header=L('Empty'), message=L('This media is unavailable'))
        #Log(codecInfos)
        #duration = int(str(codecInfos['duration']).split('.')[0]) * 1000
        #resolution = codecInfos['resolution'].split('x')
        #videoHeight = resolution[1]
        #videoWidth = resolution[0]
        #videoResolution = str(videoHeight)
        #videoCodec = str(codecInfos['video_format'])
        #audioCodec = str(codecInfos['audio_format'])

        #supportedFormats = ['mp3', 'aac', 'mp4', 'h264', 'wav']
        #if audioCodec in supportedFormats and videoCodec in supportedFormats:
        #    optimizedForStreaming = True
        #    Log('File is streamble')

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
            thumb =  Callback(Thumb, url=thumb),
            #duration = duration,
            #resolution = videoResolution
        )
    else :
        videoclip_obj = classmap[itemType](
            url =  url,
            rating_key = url,
            title = title,
            art = Callback(Thumb, url=backdrop),
            thumb =  Callback(Thumb, url=thumb),
            #duration = duration,
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
        url = 'http://cdn.letmestream.com/api/plex/frontParse/' + itemsType + '/' + str(start) + ',' + str(int(start) + int(end)) + '?token=' + lmsToken
        items = JSON.ObjectFromString(HTTP.Request(url, cacheTime = CACHE_1DAY).content)['items']
        return items
    except:
        return getItems(itemsType = itemsType, start=start, end=end)