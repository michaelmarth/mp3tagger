#!/usr/bin/env python
# encoding: utf-8
"""
tag_groupings.py

Created by Michael Marth on 2009-11-02.
Copyright (c) 2010 marth.software.services. All rights reserved.
"""

import sys
import re
import getopt
import pylast
import os.path
import ConfigParser
from mutagen.id3 import TCON, ID3, TIT1

help_message = '''
Adds ID3 tags to mp3 files for genre and groupings. Tag values are retrieved from Last.FM. Usage:
-d mp3_directory
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
		tags = last_fm_network.get_artist(artist).get_top_tags()
		for tag in tags:
			if all_genres.__contains__(tag[0].name.title()):
				genre_cache[artist] = tag[0].name.title()
				print "%20s %s" % (artist,tag[0].name.title())
				return tag[0].name.title()

def artist_to_groupings(artist):
	if groupings_cache.has_key(artist):
		return groupings_cache[artist]
	else:
		tags = last_fm_network.get_artist(artist).get_top_tags()
		relevant_tags = []
		for tag in tags:
			if int(tag[1]) >= 50:
				relevant_tags.append(tag[0].name.title())
		groupings = ", ".join(relevant_tags)
		groupings_cache[artist] = groupings
		print "%20s %s" % (artist,groupings)
		return groupings

def refine_genre(possible_refinements):
	#print "looking for refinements for %s in %s" % (possible_refinements, refinement_genre_refinements)
	for genre in possible_refinements:
		if genre in refinement_genre_refinements:
			return genre
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

def walk_mp3s():
	for root, dirs, files in os.walk('.'):
		for name in files:
			if name.endswith(".mp3"):
				audio = ID3(os.path.join(root, name))
				if not select_audio(audio):
					continue
				if tag_mode == TAG_MODE_NORMAL:
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
	if config.has_option("generic", "genres"):
		all_genres.extend(config.get("generic", "genres").split(","))
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
		walk_mp3s()		
	
	except Usage, err:
		print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
		print >> sys.stderr, "\t for help use --help"
		return 2

if __name__ == "__main__":
	sys.exit(main())
