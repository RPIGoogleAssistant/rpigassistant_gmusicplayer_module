import os
import json
import re

from gmusicapi import Mobileclient

from random import shuffle

from settings import readsettings, writesettings

from mpvplayer import mpvplayergetvolume, mpvplayer, mpvplayerstop, mpvplayercycle

from rpitts import say

googleuserid=readsettings('gmusicplayer','googleuserid')
googlepasswd=readsettings('gmusicplayer','googlepasswd')

gmapi = Mobileclient()
logged_in = gmapi.login(googleuserid, googlepasswd, Mobileclient.FROM_MAC_ADDRESS)

#'text': 'play a song Give life back to music on Google Music'
def getgmusicquerystring(querystring,querytype):
    gmregexobj = re.match( r"{'text': '((shuffle|loop)\s*(and)?\s*(shuffle|loop)?\s*)?play(.*)"+ querytype +"(.*) (on|from) .*'}", 
                 querystring, re.I|re.I|re.I|re.I|re.I|re.I)
    if gmregexobj:
       return gmregexobj.group(6)
    else:
       return ""

def updategmusiclibrary():
    if os.path.isfile("gmusicsongslibrary.json"):
       os.remove('gmusicsongslibrary.json')
    songs_library = gmapi.get_all_songs()
    with open('gmusicsongslibrary.json', 'w') as output_file:
         json.dump(songs_library, output_file)
    return songs_library

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
        if querystring.lower() in (songs_list[i][querydescription]).lower():
            song_ids.append(songs_list[i]['id'])
    songsnum=len(song_ids)
    if songsnum == 0:
       say('No songs found for '+querydescription+' '+querystring+' on your library')
    else:
       with open('gmusicplaylist.json', 'w') as output_file:
            json.dump(song_ids, output_file)

def playgmusicsongfromplaylist(index):
    if os.path.isfile("gmusicplaylist.json"):
       with open('gmusicplaylist.json','r') as input_file:
            songs_list=json.load(input_file)
            song_id=songs_list[index]
            streamurl=gmapi.get_stream_url(song_id)
            mpvplayer(mpvplayergetvolume(),streamurl)
    else:
       say('Your playlist is empty')

def playgmusicplaylist(**kwargs):
    if os.path.isfile("gmusicplaylist.json"):
       loop = kwargs.get('loop', False)
       playlistshuffle = kwargs.get('shuffle', False)
       while True:
             with open('gmusicplaylist.json','r') as input_file:
                  songs_list=json.load(input_file)
                  if playlistshuffle:
                     shuffle(songs_list)
                  playlistlength=len(songs_list)
                  for tracknum in range(0,playlistlength):
                      streamurl=gmapi.get_stream_url(songs_list[tracknum])
                      mpvplayer(mpvplayergetvolume(),streamurl)
                      if not gmusicplayercontinueplayback():
                         break
             if loop == False:
                if os.path.isfile("gmusicplaylist.json"):
                   os.remove("gmusicplaylist.json")
                break
    else:
       say('Your playlist is empty')

def gmusicselect(phrase):
    if 'artist'.lower() in phrase:
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

def stopgmusicplayer():
    mpvplayerstop()
    if os.path.isfile("gmusicplaylist.json"):
       os.remove("gmusicplaylist.json")

def gmusicplayercontinueplayback():
    if os.path.isfile("gmusicplaylist.json"):
       return True
    else:
       return False


#creategmusicplaylist('daft punk','albumArtist')
#playgmusicplaylist(shuffle=True)
#gmusicselect("{'text': 'play a song Give life back to music on Google Music'}")
#gmusicselect("{'text': 'shuffle and play artist daft punk from google music'}")
#gmusicselect('{play album songs by me from google music}')
#gmusicselect('{play song give life back to music on google music}')
