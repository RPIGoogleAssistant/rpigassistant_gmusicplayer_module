import os
import json
import re
import string

from gmusicapi import Mobileclient

from random import shuffle

from settings import readsettings, writesettings

from mpvplayer import mpvplayergetvolume, mpvplayer, mpvplayerstop, mpvplayercycle, mpvplayergetskip,  mpvplayersetskip

from rpitts import say

#Read settings from gmusicplayer.json
googleuserid=readsettings('gmusicplayer','googleuserid')
googlepasswd=readsettings('gmusicplayer','googlepasswd')

#API settings
gmapi = Mobileclient()
logged_in = gmapi.login(googleuserid, googlepasswd, Mobileclient.FROM_MAC_ADDRESS)

#To remove punctuations from query string.
removepunct = str.maketrans('', '', string.punctuation)

#Parsing query statement
def getgmusicquerystring(querystring,querytype):
    gmregexobj = re.match( r"((shuffle|loop)\s*(and)?\s*(shuffle|loop)?\s*)?play\s*(.*)?\s*"+ querytype +"\s*(.*)\s*(on|from)?\s*(.*)?", 
                 querystring, re.I|re.I|re.I|re.I|re.I|re.I)
    if gmregexobj:
       return gmregexobj.group(6)
    else:
       return ""

#Update songs list json from your Google Play Music Library
#https://play.google.com/music/listen?authuser&u=0#/albums
def updategmusiclibrary():
    if os.path.isfile("gmusicsongslibrary.json"):
       os.remove('gmusicsongslibrary.json')
    songs_library = gmapi.get_all_songs()
    with open('gmusicsongslibrary.json', 'w') as output_file:
         json.dump(songs_library, output_file)
    return songs_library

#Update playlists json from your Google Play Music play lists.
#https://play.google.com/music/listen?authuser&u=0#/wmp
def updategmusicplaylistlibrary():
    if os.path.isfile("gmusicplaylistlibrary.json"):
       os.remove('gmusicplaylistlibrary.json')
    songs_library = gmapi.get_all_user_playlist_contents()
    with open('gmusicplaylistlibrary.json', 'w') as output_file:
         json.dump(songs_library, output_file)
    return songs_library

#Create playlist from gmusicsongslibrary.json using query
#and create local playlist gmusicplaylist.json containg a particular song or
#songs by an artist or an ablum..
def creategmusicplaylist(query,querydescription):
    if os.path.isfile("gmusicplaylist.json"):
       os.remove('gmusicplaylist.json')
    songs_list=[]
    song_ids=[]
    querystring=str(query)
    if os.path.isfile("gmusicsongslibrary.json"):
       with open('gmusicsongslibrary.json','r') as input_file:
            songs_list=json.load(input_file)
    else:
       songs_list=updategmusiclibrary()
    for i in range(0,len(songs_list)):
        if (querydescription == 'PlayAllSongs'):
            song_ids.append(songs_list[i]['id'])
        elif (querystring.lower().translate(removepunct) in
           (songs_list[i][querydescription]).lower().translate(removepunct)):
            song_ids.append(songs_list[i]['id'])
    songsnum=len(song_ids)
    if songsnum == 0:
       say('No songs found for '+querydescription+' '+querystring+' on your library')
    else:
       with open('gmusicplaylist.json', 'w') as output_file:
            json.dump(song_ids, output_file)

#Select playlist from gmusicplaylistlibrary.json using query
#and create local playlist gmusicplaylist.json with songs from selected playlist.
def selectgmusicplaylist(query):
    if os.path.isfile("gmusicplaylist.json"):
       os.remove('gmusicplaylist.json')
    playlist_list=[]
    songs_list=[]
    song_ids=[]
    querystring=str(query)
    if os.path.isfile("gmusicplaylistlibrary.json"):
       with open('gmusicplaylistlibrary.json','r') as input_file:
            playlist_list=json.load(input_file)
    else:
       playlist_list=updategmusicplaylistlibrary()
    for playlistitem in playlist_list:
        if (playlistitem['name'].lower() == querystring.lower()):
           for songs_list in playlistitem['tracks']:
               song_ids.append(songs_list['trackId'])
    songsnum=len(song_ids)
    if songsnum == 0:
       say('No play list found with name '+querystring+' on your library or it is empty')
    else:
       with open('gmusicplaylist.json', 'w') as output_file:
            json.dump(song_ids, output_file)

#Play nth song from current gmusicplayer playlist
def playgmusicsongfromplaylist(index):
    if os.path.isfile("gmusicplaylist.json"):
       with open('gmusicplaylist.json','r') as input_file:
            songs_list=json.load(input_file)
            song_id=songs_list[index]
            streamurl=gmapi.get_stream_url(song_id)
            mpvplayer(mpvplayergetvolume(),streamurl)
    else:
       say('Your playlist is empty')

#Music player
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
                      streamurl=gmapi.get_stream_url(songs_list[tracknum])
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

#Selecting correct process for generating playlist from query string.
def gmusicselect(phrase):
    if ('all songs'.lower() in phrase):
       say('Playing all songs in your library')
       creategmusicplaylist(' ','PlayAllSongs')
    elif 'playlist'.lower() in phrase:
       playlist=getgmusicquerystring(phrase,'playlist').strip().lower()
       say('Getting songs from playlist '+ playlist)
       selectgmusicplaylist(playlist)
    elif 'artist'.lower() in phrase:
       artist=getgmusicquerystring(phrase,'artist').strip().lower()
       say('Getting songs by artist '+ artist)
       creategmusicplaylist(artist,'albumArtist')
    elif 'album'.lower() in phrase:
       album=getgmusicquerystring(phrase,'album').strip().lower()
       say('Getting songs in album '+ album)
       creategmusicplaylist(album,'album')
    elif 'song'.lower() in phrase:
       song=getgmusicquerystring(phrase,'song').strip().lower()
       say('Getting song '+ song)
       creategmusicplaylist(song,'title')
    else:
       say('Sorry you did not say the correct keywords')

#Stop gmusic player
def stopgmusicplayer():
    mpvplayerstop()
    if os.path.isfile("gmusicplaylist.json"):
       os.remove("gmusicplaylist.json")

#Check if to continue playing current playlist.
def gmusicplayercontinueplayback():
    if os.path.isfile("gmusicplaylist.json"):
       return True
    else:
       return False

