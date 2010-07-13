#!/usr/bin/env python
# encoding: utf-8
"""
tag_groupings.py

Created by Michael Marth on 2009-11-02.
Copyright (c) 2010 marth.software.services. All rights reserved.

( This is Tecuya's fork: http://github.com/Tecuya/mp3tagger/ )
"""

import sys
import re
import getopt
import pylast
import os.path
import ConfigParser
import cPickle
import time

from mutagen.id3 import TCON, ID3, TIT1
from mutagen.oggvorbis import OggVorbis
from mutagen.flac import FLAC

config_file = os.path.expanduser('~/.mp3tagger_genres.cfg')

# lastfm tag cache
cache_file = os.path.expanduser('~/.mp3tagger_cache.pickle')
if os.path.isfile(cache_file):
        try:
                lastfm_tag_cache = cPickle.load( file(cache_file,'r') )
                print 'Loaded cached tags for %d artists' % len(lastfm_tag_cache.keys())
        except Exception, e:
                print 'Failed loading tag cache file %s: %s' % (cache_file, e)
                sys.exit()
else:
        lastfm_tag_cache = {}

# set the last cache write date to now
last_cache_write = int(time.time())

# write cache every 5 minutes
write_cache_every = 300


help_message = '''
Adds ID3 tags to mp3 files for genre and groupings. Tag values are retrieved from Last.FM. Usage:
-d mp3_directory
-m [ask|simulation]  
   Alter the tagging mode:
   "ask" - Ask before writing
   "simulation" - Simulate only, do not modify files
-r [genre]   
   Refine the named genre to the next-most-popular last.fm tag (mp3 only!)
'''

class Usage(Exception):
	def __init__(self, msg):
		self.msg = msg

RUN_MODE_NORMAL = 0
RUN_MODE_SIMULATION = 1
RUN_MODE_ASK = 2

TAG_MODE_NORMAL = 0
TAG_MODE_REFINE = 1

def get_lastfm_tags(artist):
        if lastfm_tag_cache.has_key( artist.lower() ):
                return lastfm_tag_cache[ artist.lower() ]
        else:
                try:
                        print 'Last.fm tag lookup for artist: %s' % artist
                        lastfm_tags = last_fm_network.get_artist(artist).get_top_tags()
                except Exception, e:
                        print "ERROR: Artist '%s' failed last.fm lookup: %s" % ( artist, e )
                        lastfm_tags = []

                j=0
                tags = []
                for i in range(0,len(lastfm_tags)):
                        if lastfm_tags[i].weight > 50:
                                try:
                                        tags.append( unicode(lastfm_tags[i].item).title() )
                                except Exception, e:
                                        print 'Could not parse genre %s : %s' % (lastfm_tags[i].item, e)
                                        continue

                                j += 1
                                if j > 5:
                                        break

                # add to cache
                lastfm_tag_cache[ artist.lower() ] = tags
                                
                write_tag_cache()

                return tags


def write_tag_cache(force = False):
        global last_cache_write

        # write cache to disk if it is deemed time, or we were instructed to force write
        if force or (int(time.time()) - last_cache_write) > write_cache_every:
                print 'Writing tag cache to disk..' 

                cache_file_obj = file(cache_file, 'w+')
                cPickle.dump( lastfm_tag_cache, cache_file_obj )
                cache_file_obj.close()

                last_cache_write = int(time.time())

        
def artist_to_genre(artist):
        for tag in get_lastfm_tags(artist):
                if all_genres.__contains__(tag):
                        return tag

def artist_to_groupings(artist):
        relevant_tags = []
        for tag in get_lastfm_tags(artist):
                relevant_tags.append(tag)
        groupings = ", ".join(relevant_tags)
        return groupings

def refine_genre(possible_refinements):
	for genre in possible_refinements:
		if genre.strip() in refinement_genre_refinements:
			return genre.strip()
	return ""

def select_audio(audio):
	if tag_mode == TAG_MODE_NORMAL:
		return True
	elif audio.has_key("TCON"):
		if audio["TCON"].text[0] == refinement_genre:
			return True
		else:
			return False
	else:
		return False

def walk_audio_files():
        
        tag_count = 0

	for root, dirs, files in os.walk('.'):
		for name in files:
                        
                        audio_set = False

			if name.lower().endswith(".mp3"):
                                try:
                                        audio = ID3(os.path.join(root, name))
                                except Exception, e:
                                        print 'ERROR: ID3 Error %s : %s' % (e, os.path.join(root, name))
                                        continue

				if not select_audio(audio):
					continue
				if tag_mode == TAG_MODE_NORMAL and audio.has_key('TPE1'):
					artist = audio["TPE1"]
					genre = artist_to_genre(artist[0])
					grouping = artist_to_groupings(artist[0])
					if genre != None:
						audio["TCON"] = TCON(encoding=3, text=genre)
                                                audio_set = True
					if grouping != None:
						audio["TIT1"] = TIT1(encoding=3, text=grouping)
                                                audio_set = True
				else:
					if audio.has_key("TIT1"):
						genre = refine_genre(audio["TIT1"].text[0].split(","))
						if genre != "":
							print "Refining genre for artist %s from %s to %s" % (audio["TPE1"].text[0], audio["TCON"].text[0], genre)
							audio["TCON"] = TCON(encoding=3, text=genre)
                                                        audio_set = True


                        elif name.lower().endswith(".ogg"):
                                try:
                                        audio = OggVorbis(os.path.join(root, name))
                                except Exception, e:
                                        print 'ERROR: Ogg Comment Error %s : %s' % (e, os.path.join(root, name))
                                        continue

                                if not audio.has_key('artist'):
                                        print 'ERROR: Vorbis comment has no "artist" key in file %s' % os.path.join(root, name)
                                        continue

                                artist = audio['artist']
                                genre = artist_to_genre(artist[0])
                                if genre != None:
                                        audio["genre"] = genre
                                        audio_set = True


                        elif name.lower().endswith(".flac"):
                                try:
                                        audio = FLAC(os.path.join(root, name))
                                except Exception, e:
                                        print 'ERROR: Flac Comment Error %s : %s' % (e, os.path.join(root, name))
                                        continue
                                
                                if not audio.has_key('artist'):
                                        print 'ERROR: Vorbis comment has no "artist" key in file %s' % os.path.join(root, name)
                                        continue

                                
                                artist = audio['artist']
                                genre = artist_to_genre(artist[0])
                                if genre != None:
                                        audio["genre"] = genre
                                        audio_set = True
                                        
                                
                        if audio_set:

                                try:
                                        tag_count += 1
                                        print "* %d %s %s" % (tag_count, genre, os.path.join(root, name))

                                        # what shall we do with the file?
                                        if run_mode == RUN_MODE_NORMAL:
                                                #print "saving file %s" % (name)
                                                audio.save()
                                        if run_mode == RUN_MODE_SIMULATION:
                                                #print "not saving file %s (simulation mode)" % (name)
                                                pass
                                        if run_mode == RUN_MODE_ASK:
                                                yesno = raw_input("Save for file " + name + " (y/n) [y]")
                                                if yesno == "y" or yesno == "":
                                                        audio.save()
                                except Exception, e:
                                        print 'ERROR: Failed saving changes to file %s : %s' % (e, os.path.join(root, name))
                                


def setup_genres():
	global all_genres
	global refinement_genre_refinements	
	all_genres = TCON.GENRES
	config = ConfigParser.ConfigParser()
	config.read(config_file)
	for section in config.sections():
		for option in config.options(section):
			all_genres.extend(config.get(section, option).split(","))
	if refinement_genre != "":
		if config.has_section("refinements"):
			if config.has_option("refinements", refinement_genre):
				refinement_genre_refinements = config.get("refinements", refinement_genre).split(",")
			else:
				print "WARNING: you are running in refinement mode, but there are no refinements for genre %s defined" % (refinement_genre)
		else:
			print "WARNING: you are running in refinement mode, but there are no refinements defined"

def setup_lastfm():
	global last_fm_network
	config = ConfigParser.ConfigParser()
	config.read(os.path.expanduser('~/.mp3tagger.cfg'))
	if config.has_option("last.fm", "key") and config.has_option("last.fm", "secret"):
		API_KEY = config.get("last.fm", "key")
		API_SECRET = config.get("last.fm", "secret")
	else:
		new_config = ConfigParser.SafeConfigParser()
		new_config.add_section("last.fm")
		new_config.set("last.fm", "key", raw_input("Enter your Last.fm key:"))
		new_config.set("last.fm", "secret", raw_input("Enter your Last.fm secret:"))
		API_KEY = new_config.get("last.fm", "key")
		API_SECRET = new_config.get("last.fm", "secret")
		print "NOTE: key and secret will be stored in ~/.mp3tagger.cfg"
		with open(os.path.expanduser('~/.mp3tagger.cfg'), 'w') as configfile:
		    new_config.write(configfile)
	last_fm_network = pylast.get_lastfm_network(api_key = API_KEY, api_secret = API_SECRET)

def main(argv=None):
		
	global run_mode
	global tag_mode
	global refinement_genre

	run_mode = RUN_MODE_NORMAL
	tag_mode = TAG_MODE_NORMAL
	refinement_genre = ""
	
	if argv is None:
		argv = sys.argv
	try:
		try:
			opts, args = getopt.getopt(argv[1:], "hvd:m:r:", ["help"])
		except getopt.error, msg:
			raise Usage(msg)
		# setup last.fm network
		setup_lastfm()
		
		# option processing
		for option, value in opts:
			if option == "-v":
				verbose = True
			if option in ("-h", "--help"):
				raise Usage(help_message)
			if option in ("-m"):
				if value == "simulation":
					run_mode = RUN_MODE_SIMULATION
					print "Running in simulation mode - nothing will be saved"
				if value == "ask":
					run_mode = RUN_MODE_ASK
			if option in ("-r"):
				refinement_genre = value
				tag_mode = TAG_MODE_REFINE
				print "refining genre %s" % (refinement_genre)
			if option in ("-d"):
				try:
					os.chdir(value)
				except Exception,e:
					print "error with directory " + value
					print e
		setup_genres()
		walk_audio_files()		
                write_tag_cache(True)

	except Usage, err:
		print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
		print >> sys.stderr, "\t for help use --help"
		return 2

if __name__ == "__main__":
	sys.exit(main())
