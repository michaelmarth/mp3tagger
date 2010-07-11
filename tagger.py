#!/usr/bin/env python
# encoding: utf-8
"""
tag_groupings.py

Created by Michael Marth on 2009-11-02.
Copyright (c) 2010 marth.software.services. All rights reserved.
and Tecuya's fork: http://github.com/Tecuya/mp3tagger/

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import sys
import re
import getopt
import pylast
import os.path
import ConfigParser
from mutagen.id3 import TCON, ID3, TIT1
from mutagen.oggvorbis import OggVorbis
from mutagen.flac import FLAC

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

genre_cache = {}
groupings_cache = {}

RUN_MODE_NORMAL = 0
RUN_MODE_SIMULATION = 1
RUN_MODE_ASK = 2

TAG_MODE_NORMAL = 0
TAG_MODE_REFINE = 1

def artist_to_genre(artist):
	if genre_cache.has_key(artist):
		return genre_cache[artist]
	else:
                try:
                        tags = last_fm_network.get_artist(artist).get_top_tags()
                except Exception, e:
                        print "Artist failed last.fm lookup: %s" % e
                        return None

		for tag in tags:
			if all_genres.__contains__(tag[0].name.title()):
				genre_cache[artist] = tag[0].name.title()
				print "%20s %s" % (artist,tag[0].name.title())
				return tag[0].name.title()

def artist_to_groupings(artist):
	if groupings_cache.has_key(artist):
		return groupings_cache[artist]
	else:
                try:
                        tags = last_fm_network.get_artist(artist).get_top_tags()
                except Exception, e:
                        print "Artist failed last.fm lookup: %s" % e
                        return None 
                       
		relevant_tags = []
		for tag in tags:
			if int(tag[1]) >= 50:
				relevant_tags.append(tag[0].name.title())
		groupings = ", ".join(relevant_tags)
		groupings_cache[artist] = groupings
		print "%20s %s" % (artist,groupings)
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
	for root, dirs, files in os.walk('.'):
		for name in files:
                        
                        audio_set = False

			if name.lower().endswith(".mp3"):
                                try:
                                        audio = ID3(os.path.join(root, name))
                                except Exception, e:
                                        print 'ID3 Error %s : %s' % (e, os.path.join(root, name))
                                        continue

				if not select_audio(audio):
					continue
				if tag_mode == TAG_MODE_NORMAL and audio.has_key('TPE1'):
					artist = audio["TPE1"]
					genre = artist_to_genre(artist[0])
					grouping = artist_to_groupings(artist[0])
					if genre != None:
						audio["TCON"] = TCON(encoding=3, text=genre)
					if grouping != None:
						audio["TIT1"] = TIT1(encoding=3, text=grouping)
				else:
					if audio.has_key("TIT1"):
						genre = refine_genre(audio["TIT1"].text[0].split(","))
						if genre != "":
							print "refining genre for artist %s from %s to %s" % (audio["TPE1"].text[0], audio["TCON"].text[0], genre)
							audio["TCON"] = TCON(encoding=3, text=genre)
				
                                audio_set = True


                        elif name.lower().endswith(".ogg"):
                                try:
                                        audio = OggVorbis(os.path.join(root, name))
                                except Exception, e:
                                        print 'Ogg Comment Error %s : %s' % (e, os.path.join(root, name))
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
                                        print 'Flac Comment Error %s : %s' % (e, os.path.join(root, name))
                                        continue
                                        
                                artist = audio['artist']
                                genre = artist_to_genre(artist[0])
                                if genre != None:
                                        audio["genre"] = genre
                                        audio_set = True
                                        
                                        
                        if audio_set:

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



def setup_genres():
	global all_genres
	global refinement_genre_refinements	
	all_genres = TCON.GENRES
	config = ConfigParser.ConfigParser()
	config.read(os.path.expanduser('~/.mp3tagger_genres.cfg'))
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
	
	except Usage, err:
		print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
		print >> sys.stderr, "\t for help use --help"
		return 2

if __name__ == "__main__":
	sys.exit(main())
