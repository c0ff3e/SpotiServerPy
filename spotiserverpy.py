#!/usr/bin/env python
# -*- coding: utf8 -*-

from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.renderers import render
import json
import cmd
import logging
import os
import sys
import threading
import time

from spotify import ArtistBrowser, Link, ToplistBrowser, SpotifyError
from spotify.audiosink import import_audio_sink
from spotify.manager import (SpotifySessionManager, SpotifyPlaylistManager,
    SpotifyContainerManager)
    
AudioSink = import_audio_sink()
container_loaded = threading.Event()

## playlist callbacks ##
class JukeboxPlaylistManager(SpotifyPlaylistManager):
    def tracks_added(self, p, t, i, u):
        print 'Tracks added to playlist %s' % p.name()

    def tracks_moved(self, p, t, i, u):
        print 'Tracks moved in playlist %s' % p.name()

    def tracks_removed(self, p, t, u):
        print 'Tracks removed from playlist %s' % p.name()

## container calllbacks ##
class JukeboxContainerManager(SpotifyContainerManager):
    def container_loaded(self, c, u):
        container_loaded.set()

    def playlist_added(self, c, p, i, u):
        print 'Container: playlist "%s" added.' % p.name()

    def playlist_moved(self, c, p, oi, ni, u):
        print 'Container: playlist "%s" moved.' % p.name()

    def playlist_removed(self, c, p, i, u):
        print 'Container: playlist "%s" removed.' % p.name()

class Jukebox(SpotifySessionManager):

    queued = False
    playlist = 2
    track = 0
    appkey_file = os.path.join(os.path.dirname(__file__), 'spotify_appkey.key')

    def __init__(self, *a, **kw):
        SpotifySessionManager.__init__(self, *a, **kw)
        self.audio = AudioSink(backend=self)
        self.ui = None
        self.ctr = None
        self.playing = False
        self._queue = []
        self.playlist_manager = JukeboxPlaylistManager()
        self.container_manager = JukeboxContainerManager()
        self.track_playing = None
        print "Logging in, please wait..."


    def new_track_playing(self, track):
        self.track_playing = track

    def logged_in(self, session, error):
        if error:
            print error
            return
        print "Logged in!"
        self.ctr = session.playlist_container()
        self.container_manager.watch(self.ctr)
        self.starred = session.starred()
        self.ui = server.serve_forever()
        #if not self.ui.is_alive():
        #    self.ui.start()

    def logged_out(self, session):
        print "Logged out!"

    def load_track(self, track):
        print u"Loading track..."
        while not track.is_loaded():
            time.sleep(0.1)
        if track.is_autolinked(): # if linked, load the target track instead
            print "Autolinked track, loading the linked-to track"
            return self.load_track(track.playable())
        if track.availability() != 1:
            print "Track not available (%s)" % track.availability()
        if self.playing:
            self.stop()
        self.new_track_playing(track)
        self.session.load(track)
        print "Loaded track: %s" % track.name()

    def load(self, playlist, track):
        if self.playing:
            self.stop()
        if 0 <= playlist < len(self.ctr):
            pl = self.ctr[playlist]
        elif playlist == len(self.ctr):
            pl = self.starred
        spot_track = pl[track]
        self.new_track_playing(spot_track)
        self.session.load(spot_track)
        print "Loading %s from %s" % (spot_track.name(), pl.name())

    def load_playlist(self, playlist):
        if self.playing:
            self.stop()
        if 0 <= playlist < len(self.ctr):
            pl = self.ctr[playlist]
        elif playlist == len(self.ctr):
            pl = self.starred
        print "Loading playlist %s" % pl.name()
        if len(pl):
            print "Loading %s from %s" % (pl[0].name(), pl.name())
            self.new_track_playing(pl[0])
            self.session.load(pl[0])
        for i, track in enumerate(pl):
            if i == 0:
                continue
            self._queue.append((playlist, i))

    def queue(self, playlist, track):
        if self.playing:
            self._queue.append((playlist, track))
        else:
            print 'Loading %s', track.name()
            self.load(playlist, track)
            self.play()

    def play(self):
        self.audio.start()
        self.session.play(1)
        print "Playing"
        self.playing = True

    def stop(self):
        self.session.play(0)
        print "Stopping"
        self.playing = False
        self.audio.stop()

    def music_delivery_safe(self, *args, **kwargs):
        return self.audio.music_delivery(*args, **kwargs)

    def next(self):
        self.stop()
        if self._queue:
            t = self._queue.pop(0)
            self.load(*t)
            self.play()
        else:
            self.stop()

    def end_of_track(self, sess):
        self.audio.end_of_track()

    def search(self, *args, **kwargs):
        self.session.search(*args, **kwargs)

    def browse(self, link, callback):
        if link.type() == link.LINK_ALBUM:
            browser = self.session.browse_album(link.as_album(), callback)
            while not browser.is_loaded():
                time.sleep(0.1)
            for track in browser:
                print track.name()
        if link.type() == link.LINK_ARTIST:
            browser = ArtistBrowser(link.as_artist())
            while not browser.is_loaded():
                time.sleep(0.1)
            for album in browser:
                print album.name()

    def watch(self, p, unwatch=False):
        if not unwatch:
            print "Watching playlist: %s" % p.name()
            self.playlist_manager.watch(p)
        else:
            print "Unatching playlist: %s" % p.name()
            self.playlist_manager.unwatch(p)

    def toplist(self, tl_type, tl_region):
        print repr(tl_type)
        print repr(tl_region)
        def callback(tb, ud):
            for i in xrange(len(tb)):
                print '%3d: %s' % (i+1, tb[i].name())

        tb = ToplistBrowser(tl_type, tl_region, callback)





def p_play(request):
  return {"message": "%(command)s" % request.matchdict}

def p_add(request):
  l = Link.from_string("%(link_uri)s" % request.matchdict)
  if not l.type() == Link.LINK_TRACK:
    print "You can only play tracks!"
    return
  sessionM.load_track(l.as_track()) 
  sessionM.play()
  #sessionM.queue(sessionM, "20130428", l.as_track())
  return {"message": "%(user)s Onskade %(link_uri)s" % request.matchdict}   




if __name__ == '__main__':
  config = Configurator()
  config.add_route('controller', '/controller/{command}')
  config.add_view(p_play, route_name='controller', renderer="json")
  config.add_route('add', '/add/{user}/{link_uri}')
  config.add_view(p_add, route_name='add', renderer="json")
  app = config.make_wsgi_app()
  server = make_server('0.0.0.0', 8084, app)
  
  import optparse
  op = optparse.OptionParser(version="%prog 0.1")
  op.add_option("-u", "--username", help="Spotify username")
  op.add_option("-p", "--password", help="Spotify password")
  op.add_option("-v", "--verbose", help="Show debug information",
  dest="verbose", action="store_true")
  op.add_option("-b", "--album", help="Spotify Album ID")
  (options, args) = op.parse_args()
  if options.verbose:
    logging.basicConfig(level=logging.DEBUG)
  sessionM = Jukebox(options.username, options.password, True)
  sessionM.connect()

