import os
import json
import re
import string
import random

from rpitts import say

from gmusicapi import Mobileclient

import pafy

from random import shuffle

from settings import readsettings, writesettings
from db import (create_db_connection, close_db_connection,
                commit_db_connection, create_db_table,
                insert_db_table, drop_db_table, read_db_table)

from mpvplayer import mpvplayergetvolume, mpvplayer, mpvplayerstop, mpvplayercycle, mpvplayergetskip,  mpvplayersetskip

#Read settings from gmusicplayer.json
googleuserid=readsettings('gmusicplayer','googleuserid')
googlepasswd=readsettings('gmusicplayer','googlepasswd')

#YouTube API Constants
DEVELOPER_KEY = readsettings('youtubeplayer','apikey')
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

#API settings
gmapi = Mobileclient()
logged_in = gmapi.login(googleuserid, googlepasswd, Mobileclient.FROM_MAC_ADDRESS)

pafy.set_api_key(DEVELOPER_KEY)

global musicplaylisttype
musicplaylisttype='gmusic'

#To remove punctuations from query string.
removepunct = str.maketrans('', '', string.punctuation)

#Random id generation for station generator
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

#Clear current playlist
def clearplaylists():
    if os.path.isfile("gmusicplaylist.json"):
       os.remove('gmusicplaylist.json')

#Get songs from google music library and save to database
def getsongsfromlibraryandsavetodb(tablename):
    songs_library = gmapi.get_all_songs()
    for i in range(0,len(songs_library)):
        song_items=[]
        columns = sorted(songs_library[i].keys())
        requiredcolumns = ('album','albumArtist', 'id', 'title')
        dbcolumns=list(filter(lambda x: x in requiredcolumns, columns))
        for j in dbcolumns:
            song_row = songs_library[i][j]
            if (j == 'id'):
                song_items.append(song_row)
            else:
                song_items.append(song_row.lower().translate(removepunct))
        query = "insert into {0} (album, albumArtist, id, title) values (?{1})"
        query = query.format(tablename, ",?" * (len(requiredcolumns)-1))
        insert_db_table(tablename,query,song_items)

#Get songs from playlists in google music library and save to database
def getsongsfromplaylistandsavetodb(tablename):
    playlists_library = gmapi.get_all_user_playlist_contents()
    for playlistitem in playlists_library:
       playlistname = playlistitem['name'].lower()
       tracks_library=playlistitem['tracks']
       for i in range(0,len(tracks_library)):
            songs_library=tracks_library[i]['track']
            song_id=tracks_library[i]['trackId']
            song_items=[]
            song_items.append(playlistname.lower().translate(removepunct))
            song_items.append(song_id)
            columns = sorted(songs_library.keys())
            requiredcolumns = ('name','trackId','album','albumArtist','title')
            dbcolumns=list(filter(lambda x: x in requiredcolumns, columns))
            for j in dbcolumns:
                song_row = songs_library[j]
                song_items.append(song_row.lower().translate(removepunct))
            query = "insert into {0} (name, id, album, albumArtist, title) values (?{1})"
            query = query.format(tablename, ",?" * (len(requiredcolumns)-1))
            insert_db_table(tablename,query,song_items)

#Function to save stations data to table in database
def getstationsandsavetodb(tablename):
    stations_library = gmapi.get_all_stations()
    for stationitem in stations_library:
        station_items=[]
        station_name = stationitem['name'].lower().translate(removepunct)
        station_id = stationitem['id']
        station_items.append(station_name)
        station_items.append(station_id)
        query = "insert into {0} (name, id) values (?{1})"
        query = query.format(tablename, ",?")
        insert_db_table(tablename,query,station_items)

#Save genres data to database
def getgenresandsavetodb(tablename):
    genres_library=gmapi.get_genres()
    for genresitem in genres_library:
        genres_items=[]
        genres_name = genresitem['name'].lower().translate(removepunct)
        genres_id = genresitem['id']
        genres_items.append(genres_name)
        genres_items.append(genres_id)
        query = "insert into {0} (name, id) values (?{1})"
        query = query.format(tablename, ",?")
        insert_db_table(tablename,query,genres_items)

#Save podcast data to database
def getpodcastsandsavetodb(tablename):
    podcast_library=gmapi.get_all_podcast_episodes(incremental=False, include_deleted=None, updated_after=None)
    for i in range(0,len(podcast_library)):
        podcast_items=[]
        podcast_name=podcast_library[i]['seriesTitle']
        podcast_episode=podcast_library[i]['episodeId']
        podcast_time=podcast_library[i]['publicationTimestampMillis']
        podcast_items=[podcast_name,podcast_episode,podcast_time]
        query = "insert into {0} (name, id, time) values (?{1})"
        query = query.format(tablename, ",?,?")
        insert_db_table(tablename,query,podcast_items)


#Update songs list json from your Google Play Music Library
#https://play.google.com/music/listen?authuser&u=0#/albums
def updategmusiclibrary():
    try:
       create_db_connection('gmusiclibrary.db')
       drop_db_table('gmusicsongs')
       drop_db_table('gmusicplaylists')
       drop_db_table('gmusicstations')
       drop_db_table('gmusicgenres')
       drop_db_table('gmusicpodcasts')
       create_db_table('gmusicsongs',['album','albumArtist','id','title'])
       getsongsfromlibraryandsavetodb('gmusicsongs')
       create_db_table('gmusicplaylists',['name','id','album','albumArtist','title'])
       getsongsfromplaylistandsavetodb('gmusicplaylists')
       create_db_table('gmusicstations',['name','id'])
       getstationsandsavetodb('gmusicstations')
       create_db_table('gmusicgenres',['name','id'])
       getgenresandsavetodb('gmusicgenres')
       create_db_table('gmusicpodcasts',['name','id', 'time'])
       getpodcastsandsavetodb('gmusicpodcasts')
       commit_db_connection()
       close_db_connection()
       return True
    except Exception:
       return False

#creates playlist from db
def creategmusicplaylist(**kwargs):
    clearplaylists()
    global musicplaylisttype
    musicplaylisttype='gmusic'
    song = kwargs.get('song', None)
    artist = kwargs.get('artist', None)
    album = kwargs.get('album', None)
    playlist = kwargs.get('playlist', None)
    podcast = kwargs.get('podcast', None)
    if 'playlist' in kwargs and playlist is not None:
        dbtable = kwargs.get('dbtable', 'gmusicplaylists')
    elif 'podcast' in kwargs and podcast is not None:
        dbtable = kwargs.get('dbtable', 'gmusicpodcasts')
    else:
        dbtable = kwargs.get('dbtable', 'gmusicsongs')
    create_db_connection('gmusiclibrary.db')
    querystring = "SELECT id FROM "+dbtable
    if (artist is not None) or (album is not None) or (song is not None) or (playlist is not None) or (podcast is not None):
        querystring = querystring + " WHERE"
    if (artist is not None):
        querystring = querystring + " albumArtist LIKE '%"+artist.lower().translate(removepunct).strip()+"%' AND"
    if (album is not None):
        querystring = querystring + " album LIKE '%"+album.lower().translate(removepunct).strip()+"%' AND"
    if (song is not None):
        querystring = querystring + " title LIKE '%"+song.lower().translate(removepunct).strip()+"%' AND"
    if (playlist is not None):
        querystring = querystring + " name LIKE '%"+playlist.lower().translate(removepunct).strip()+"%' AND"
    if (podcast is not None):
        querystring = querystring + " name LIKE '%"+podcast.lower().translate(removepunct).strip()+"%' AND"
    querystring = querystring + " id IS NOT NULL"
    if (podcast is not None):
       querystring = querystring + " ORDER BY time DESC"
    querystring = querystring + ";"
    songs_ids = read_db_table(querystring)
    playlist=[]
    for song in songs_ids:
        playlist.append(song[0])
    close_db_connection()
    if playlist:
       with open('gmusicplaylist.json', 'w') as output_file:
            json.dump(playlist, output_file)

#Create a playlist from station
def generateplaylistfromstation(station_id):
    clearplaylists()
    global musicplaylisttype
    musicplaylisttype='gmusic'
    station_tracks = gmapi.get_station_tracks(station_id, num_tracks=25, recently_played_ids=None)
    song_items = []
    for i in range(0,len(station_tracks)):
        song_id=station_tracks[i]['storeId']
        song_items.append(song_id)
    with open('gmusicplaylist.json', 'w') as output_file:
        json.dump(song_items, output_file)

#Create a playlist from genre
def generateplaylistfromgenre(genreid):
    station_name = genreid + id_generator()
    station_id = gmapi.create_station(station_name,genre_id=genreid)
    generateplaylistfromstation(station_id)

#Genreates playlist from google music
def generategmusicplaylist(**kwargs):
    station = kwargs.get('station', None)
    genre = kwargs.get('genre', None)
    if 'station' in kwargs:
        dbtable = kwargs.get('dbtable', 'gmusicstations')
    else:
        dbtable = kwargs.get('dbtable', 'gmusicgenres')
    create_db_connection('gmusiclibrary.db')
    querystring = "SELECT id FROM "+dbtable
    if (station is not None) or (genre is not None):
       querystring = querystring + " WHERE"
    if (station is not None):
       querystring = querystring + " name LIKE '%"+station.lower().translate(removepunct).strip()+"%' AND"
    if (genre is not None):
       querystring = querystring + " name LIKE '%"+genre.lower().translate(removepunct).strip()+"%' AND"
    querystring = querystring + " id IS NOT NULL;"
    item_ids = read_db_table(querystring)
    for item in item_ids:
        if (station is not None):
           generateplaylistfromstation(item[0])
        else:
           generateplaylistfromgenre(item[0])
    close_db_connection()

#Search google music if no match found in database
def searchgmusic(**kwargs):
    clearplaylists()
    global musicplaylisttype
    musicplaylisttype='gmusic'
    song = kwargs.get('song', None)
    artist = kwargs.get('artist', None)
    album = kwargs.get('album', None)
    playlist = kwargs.get('playlist', None)
    station = kwargs.get('station', None)
    podcast = kwargs.get('podcast', None)
    situation = kwargs.get('sitaution', None)
    video = kwargs.get('video', None)
    searchquery=''
    if (song is not None):
       searchquery=searchquery+" "+song
    if (artist is not None):
       searchquery=searchquery+" "+artist
    if (album is not None):
       searchquery=searchquery+" "+album
    if (playlist is not None):
       searchquery=searchquery+" "+playlist
    if (station is not None):
       searchquery=searchquery+" "+station
    if (podcast is not None):
       searchquery=searchquery+" "+podcast
    searchquery=searchquery.strip()
    search_results=gmapi.search(searchquery,max_results=10)
    song_hits = search_results['song_hits']
    album_hits = search_results['album_hits']
    artist_hits = search_results['artist_hits']
    playlist_hits = search_results['playlist_hits']
    podcast_hits = search_results['podcast_hits']
    station_hits = search_results['station_hits']
    situation_hits = search_results['situation_hits']
    video_hits = search_results['video_hits']
    if (song is not None and not(len(song_hits) == 0)):
        song_ids=[]
        for i in range(0,len(song_hits)):
            songs_list=song_hits[i]['track']
            song_ids.append(songs_list['storeId'])
        if song_ids:
           with open('gmusicplaylist.json', 'w') as output_file:
                json.dump(song_ids, output_file)
    elif (album is not None and not(len(album_hits) == 0)):
       album_id=album_hits[0]['album']['albumId']
       album_item=gmapi.get_album_info(album_id, include_tracks=True)
       album_tracks=album_item['tracks']
       song_ids=[]
       for i in range(0,len(album_tracks)):
            song_id=album_tracks[i]['nid']
            song_ids.append(song_id)
       if song_ids:
          with open('gmusicplaylist.json', 'w') as output_file:
               json.dump(song_ids, output_file)
    elif (artist is not None and not(len(artist_hits) == 0)):
       artist_id=artist_hits[0]['artist']['artistId']
       artist_item=gmapi.get_artist_info(artist_id, max_top_tracks=50)
       artist_tracks=artist_item['topTracks']
       song_ids=[]
       for i in range(0,len(artist_tracks)):
            song_id=artist_tracks[i]['nid']
            song_ids.append(song_id)
       if song_ids:
          with open('gmusicplaylist.json', 'w') as output_file:
               json.dump(song_ids, output_file)
    elif (station is not None and not(len(station_hits) == 0)):
       station_seed = station_hits[0]['station']['seed']
       song_ids=[]
       for key, value in station_seed.items():
           if key.lower().endswith('id'):
              seed_id = value
              if (key == 'trackId'):
                 song_ids.append(seed_id)
                 if song_ids:
                    with open('gmusicplaylist.json', 'w') as output_file:
                         json.dump(song_ids, output_file)
                 station_id = None
              elif (key == 'artistId'):
                 station_id = gmapi.create_station(searchquery,artist_id=seed_id)
              elif (key == 'albumId'):
                 station_id = gmapi.create_station(searchquery,album_id=seed_id)
              else:
                 station_id = None
       if ( station_id is not None ):
          station_tracks = gmapi.get_station_tracks(station_id, num_tracks=25)
          for i in range(0,len(station_tracks)):
              song_ids.append(station_tracks[i]['storeId'])
          if song_ids:
             with open('gmusicplaylist.json', 'w') as output_file:
                  json.dump(song_ids, output_file)
    elif (not(len(video_hits) == 0)):
        musicplaylisttype='youtube'
        video_ids=[]
        for i in range(0,len(video_hits)):
            video_ids.append(video_hits[i]['youtube_video']['id'])
        if video_ids:
            with open('gmusicplaylist.json', 'w') as output_file:
                 json.dump(video_ids, output_file)
    else:
        say('No results found')

#Generate song url from song_id
def getgmusicsongurl(song_id):
    if gmapi.is_subscribed:
       try:
          if song_id.startswith('D'):
            song_url = gmapi.get_podcast_episode_stream_url(song_id)
          else:
            song_url = gmapi.get_stream_url(song_id)
       except Exception:
          song_url = None
    else:
      station_name = id_generator()
      station_id = gmapi.create_station(station_name,track_id=song_id)
      station_info = gmapi.get_station_info(station_id, num_tracks=25)
      session_token = station_info['sessionToken']
      station_tracks = station_info['tracks']
      for i in range(0,len(station_tracks)):
          if (station_tracks[i]['storeId'] == song_id):
             wentry_id = station_tracks[i]['wentryid']
             try:
                song_url=gmapi.get_station_track_stream_url(song_id, wentry_id, session_token)
             except Exception:
                song_url = None
    return song_url

#Get url from youtube from video_id
def getyoutubesongurl(video_id):
    youtube_url="http://www.youtube.com/watch?v=" + video_id
    try:
       youtube_video = pafy.new(youtube_url)
       bestaudio = youtube_video.getbestaudio()
       song_url=bestaudio.url
       return song_url
    except Exception:
       return None

#Identify youtube playlist type (Youtbue/GMusic
def getgmusicplaylisttype():
    if 'musicplaylisttype' in globals():
       return musicplaylisttype
    else:
       return None

#Get streaming url from id
def getgmusicstreamurl(music_id):
    musicplaylisttype=getgmusicplaylisttype()
    if (musicplaylisttype == "youtube"):
        song_url=getyoutubesongurl(music_id)
    else:
        song_url=getgmusicsongurl(music_id)
    return song_url


#Play music
def playgmusicplaylist(**kwargs):
    if os.path.isfile("gmusicplaylist.json"):
       loop = kwargs.get('loop', False)
       playlistshuffle = kwargs.get('shuffle', False)
       while True:
             with open('gmusicplaylist.json','r') as input_file:
                  songs_list=json.load(input_file)
                  playlistlength=len(songs_list)
                  if (playlistshuffle and  playlistlength > 1):
                     say('Shuffling playlist')
                     shuffle(songs_list)
                  tracknum = 0
                  while tracknum < playlistlength:
                      streamurl=getgmusicstreamurl(songs_list[tracknum])
                      mpvplayer(mpvplayergetvolume(),streamurl)
                      if (mpvplayergetskip() == 0):
                         tracknum = tracknum + 1
                      else:
                         tracknum = tracknum + mpvplayergetskip()
                      mpvplayersetskip(0)
                      if (tracknum < 0 or tracknum >= playlistlength):
                         say('End of playlist')
                      if not gmusicplayercontinueplayback():
                         break
             if loop == False:
                if os.path.isfile("gmusicplaylist.json"):
                   os.remove("gmusicplaylist.json")
                break
             else:
                if not gmusicplayercontinueplayback():
                   break
                else:
                   say('Loop playing current playlist')
    else:
       say('Your playlist is empty')

#Stop media player
def stopgmusicplayer():
    mpvplayerstop()
    clearplaylists()

#Check if to continue playing current playlist.
def gmusicplayercontinueplayback():
    if os.path.isfile("gmusicplaylist.json"):
       return True
    else:
       return False

