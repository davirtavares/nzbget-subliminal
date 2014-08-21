#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Subliminal post-processing script for NZBGet
#
# Copyright (C) 2014 Chris Caron <lead2gold@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with subliminal.  If not, see <http://www.gnu.org/licenses/>.
#

##############################################################################
### NZBGET POST-PROCESSING/SCHEDULER SCRIPT                                ###

# Download Subtitles.
#
# The script searches subtitles on various web-sites and saves them into
# destination directory near video files.
#
# This post-processing script is a wrapper for "Subliminal",
# a python library to search and download subtitles, written
# by Antoine Bertin (Diaoul Ael). All credit goes to the original author.
#
# Info about this Subliminal NZB Script:
# Author: Chris Caron (lead2gold@gmail.com).
# Date: Fri, Aug 8th, 2014.
# License: GPLv3 (http://www.gnu.org/licenses/gpl.html).
# Script Version: 0.5.0.
#
# NOTE: This script requires Python to be installed on your system.
#
# NOTE: Addic7ed (http://www.addic7ed.com/) is only utilized if a valid
#       username and password is provided.

##############################################################################
### OPTIONS                                                                ###

# List of language codes.
#
# Language code according to ISO 639-1.
# Few examples: English - en, German - de, Dutch - nl, French - fr.
# For the full list of language codes see
#     http://www.loc.gov/standards/iso639-2/php/English_list.php.

# Language Setting
#
# Subtitles for multiple languages can be downloaded. Separate multiple
# languages with some type of delmiter (space, comma, etc)
# codes with commas. Example: en, fr
#Languages=en

# Subliminal Single Mode Setting (yes, no).
#
# Download content without the language code in the subtitles filename.
# Note: this is forced to 'no' in the event more then one Language
# is specified.
#Single=yes

# Overwrite Mode (yes, no).
#
# Overwrite existing subtitles if they exist.
#Overwrite=no

# Hearing Impaired Enabled (yes, no).
#
# download hearing impaired subtitles
#HearingImpaired=no

# Search Mode (basic, advanced).
#
# basic    - presumed subtitles are guessed based on the (deobsfucated)
#            filename alone.
# advanced - presumed subtiltes are guessed based on the (deobsfucated)
#            filename (same as basic).  But further processing occurs to
#            help obtain more accurate results. Meta data extracted from
#            the actual video in question such as it's length, FPS, and
#            encoding (including if subs are already included or not).
#            This mode yields the best results but at the cost of additional
#            time and CPU.
#SearchMode=advanced

# Subtitle Providers
#
# Supply a list of providers you want to include in your query
# separated by a comma and or space. The default (if none is
# specified then the following defaults are used: opensubtitles, tvsubtitles,
# podnapisi, addic7ed, thesubdb
#Providers=opensubtitles, tvsubtitles, podnapisi, addic7ed, thesubdb

# Addic7ed Username
#
# If you wish to utilize the addic7ed provider, you are additionally required
# to provide a username and password. Specify the `username` here.
#Addic7edUsername=

# Addic7ed Password
#
# If you wish to utilize the addic7ed provider, you are additionally required
# to provide a username and password. Specify the `password` here.
#Addic7edPassword=

# File extensions for video files.
#
# Only files with these extensions are processed. Extensions must
# be separated with commas.
# Example=.mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso
#VideoExtensions=.mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso

# Cache Directory
#
# This directory is used for storing temporary cache files created when
# fetching subtitles.
#CacheDir=${TempDir}/subliminal

# Enable debug logging (yes, no).
#
# If subtitles are not downloaded as expected, activate debug logging
# to get a verbose output from subliminal.
#Debug=no

### POST-PROCESSING MODE                                                   ###

# List of TV categories.
#
# Comma separated list of categories for TV. VideoSort automatically
# distinguishes movies from series and dated TV shows. But it needs help
# to distinguish movies from other TV shows because they are named
# using same conventions. If a download has associated category listed in
# option <TvCategories>, VideoSort uses this information.
#
# Category names must match categories defined in NZBGet.
#TvCategories=tv, tv2

### SCHEDULER MODE                                                         ###

# Directories to Scan
#
# Specify any number of directories this script can (recursively) check
# delimited by a comma and or space. ie: /home/nuxref/mystuff, /path/no3, etc
# For windows users, you can specify: C:\My Downloads, \\My\Network\Path, etc
#ScanDirectories=

# Maximum File Age
#
# The maximum amount of time that can elapse before we can assume that if
# there are still no subtitles after this duration, then there never will
# be.  This option prevents thrashing and requesting subtitles for something
# over and over again for no reason. This value is identified in hours
# relative to each file checked
#MaxAge=24

### NZBGET POST-PROCESSING/SCHEDULER SCRIPT                                ###
##############################################################################

import re
from os.path import join
from shutil import move
from os import getcwd
from os.path import split
from os.path import basename
from os.path import abspath
from os.path import dirname
from os.path import splitext
from os.path import isfile
from os.path import isdir
from os import unlink
from os import makedirs
import logging

# This is required if the below environment variables
# are not included in your environment already
import sys
sys.path.insert(0, join(dirname(__file__), 'Subliminal'))

# Script dependencies identified below
from guessit import matcher
from datetime import timedelta
from datetime import datetime
from subliminal import Video
from subliminal import MutexLock
from subliminal import cache_region
from subliminal import scan_videos
from subliminal import download_best_subtitles
import babelfish

# pynzbget Script Wrappers
from nzbget import PostProcessScript
from nzbget import SchedulerScript
from nzbget import EXIT_CODE
from nzbget import SCRIPT_MODE

class SEARCH_MODE(object):
    BASIC = "basic"
    ADVANCED = "advanced"

# Some Default Environment Variables (used with CLI)
DEFAULT_EXTENSIONS = \
        '.mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso'
DEFAULT_MAXAGE = 24
DEFAULT_LANGUAGE = 'en'
DEFAULT_PROVIDERS = [
    'opensubtitles',
    'tvsubtitles',
    'podnapisi',
    'addic7ed',
    'thesubdb',
]
DEFAULT_SINGLE = 'yes'
DEFAULT_FORCE = 'no'
DEFAULT_HEARING_IMPAIRED = 'no'
DEFAULT_SEARCH_MODE = SEARCH_MODE.ADVANCED

# A list of compiled regular expressions identifying files to not parse ever
IGNORE_FILELIST_RE = (
    # Samples
    re.compile('^.*[-.]sample(\.[^.]*)?$', re.IGNORECASE),
)

# stat is used to filter files by age
from stat import ST_MTIME
from os import stat

class SubliminalScript(PostProcessScript, SchedulerScript):
    """A wrapper to Subliminal written for NZBGet
    """

    def filter_files_by_age(self, files, maxage):
        """ Used to filter file list by their age
        """
        _files = []
        ref_time = datetime.now() - timedelta(hours=maxage)
        for _file in files:
            try:
                m_time = datetime.fromtimestamp(stat(_file)[ST_MTIME])
            except:
                self.logger.debug('File not found, skipping %s' % _file)
                continue

            if m_time < ref_time:
                self.logger.debug('To old, skipping %s' % _file)
                continue

            _files.append(_file)
        return _files

    def apply_nzbheaders(self, guess):
        """ Applies NZB headers (if exist) """

        nzb_used = False

        nzb_proper_name = self.nzb_get('propername', '')
        nzb_episode_name = self.nzb_get('episodename', '')
        nzb_movie_year = self.nzb_get('movieyear', '')
        nzb_more_info = self.nzb_get('moreinfo', '')

        if nzb_proper_name != '':
            nzb_used = True
            self.logger.debug('Using DNZB-ProperName')
            if guess['vtype'] == 'series':
                proper_name = nzb_proper_name
                guess['series'] = proper_name
            else:
                guess['title'] = nzb_proper_name

        if nzb_episode_name != '' and guess['vtype'] == 'series':
            nzb_used = True
            self.logger.debug('Using DNZB-EpisodeName')
            guess['title'] = nzb_episode_name

        if nzb_movie_year != '':
            nzb_used = True
            self.logger.debug('Using DNZB-MovieYear')
            guess['year'] = nzb_movie_year

        if nzb_more_info != '':
            nzb_used = True
            self.logger.debug('Using DNZB-MoreInfo')
            if guess['type'] == 'movie':
                regex = re.compile(
                    r'^http://www.imdb.com/title/(tt[0-9]+)/$', re.IGNORECASE)
                matches = regex.match(nzb_more_info)
                if matches:
                    guess['imdb'] = matches.group(1)
                    guess['cpimdb'] = 'cp(' + guess['imdb'] + ')'

        if nzb_used:
            self.logger.debug(guess.nice_string())

    def guess_info(self, filename, shared,
                   deobfuscate=True, use_nzbheaders=True):
        """ Parses the filename using guessit-library """

        tv_categories = [
            cat.lower() for cat in \
            self.parse_list(self.get('TvCategories', [])) ]

        if deobfuscate:
            filename = self.deobfuscate(filename)

        self.logger.debug('Guessing using: %s' % filename)

        # Push Guess to NZBGet
        if shared:
            guess = self.pull_guess()
        else:
            guess = None

        if not guess:
            _matcher = matcher.IterativeMatcher(
                unicode(filename),
                filetype='autodetect',
                opts=['nolanguage', 'nocountry'],
            )
            mtree = _matcher.match_tree
            guess = _matcher.matched()

            if self.vdebug:
                # Verbose Mode Only
                self.logger.vdebug(mtree)
                for node in mtree.nodes():
                    if node.guess:
                        self.logger.vdebug(node.guess)
                self.logger.vdebug(guess.nice_string())

            # fix some strange guessit guessing:
            # if guessit doesn't find a year in the file name it
            # thinks it is episode, but we prefer it to be handled
            # as movie instead
            if guess.get('type') == 'episode' and \
                    guess.get('episodeNumber', '') == '':
                guess['type'] = 'movie'
                guess['title'] = guess.get('series')
                guess['year'] = '1900'
                self.logger.debug(
                    'An episode without episode # becomes a movie',
                )
                self.logger.debug(guess.nice_string())

            # detect if year is part of series name
            if guess['type'] == 'episode':
                last_node = None
                for node in mtree.nodes():
                    if node.guess:
                        if last_node != None and \
                                node.guess.get('year') != None and \
                                last_node.guess.get('series') != None:
                            guess['series'] += ' ' + str(guess['year'])
                            self.logger.debug('Detected year as part of title.')
                            self.logger.debug(guess.nice_string())
                            break
                        last_node = node

            if guess['type'] == 'movie':
                category = self.get('CATEGORY', '').lower()
                force_tv = category in tv_categories

                date = guess.get('date')
                if date:
                    guess['vtype'] = 'dated'
                elif force_tv:
                    guess['vtype'] = 'othertv'
                else:
                    guess['vtype'] = 'movie'

            elif guess['type'] == 'episode':
                guess['vtype'] = 'series'
        else:
            self.logger.debug('Guessed content already provided by NZBGet!')

        self.logger.debug('Type: %s' % guess['vtype'])

        if use_nzbheaders:
            # Apply nzb meta information to guess if present
            self.apply_nzbheaders(guess)

        if shared:
            # Push Guess to NZBGet
            self.push_guess(guess)

        return guess

    def subliminal_fetch(self, files, single_mode=True, shared=True,
                         deobfuscate=True, use_nzbheaders=True):
        """This function fetches the subtitles
        """

        # Get configuration
        overwrite = self.parse_bool(self.get('Overwrite', 'no'))
        cache_dir = self.get('CACHEDIR', self.get('TEMPDIR'))
        cache_file = join(cache_dir, 'subliminal.cache.dbm')

        # Search Mode
        search_mode = self.get('SearchMode', DEFAULT_SEARCH_MODE)
        self.logger.info('Using %s search mode' % search_mode)

        if not isdir(cache_dir):
            try:
                makedirs(cache_dir)
            except:
                self.logger.error('Could not create directory %s' % (
                    cache_dir,
                ))

        # Handle providers, if list is empty, then use default
        # however, if there is content, parse it and remove entries
        # that are not valid
        providers = self.parse_list(
            self.get('Providers', DEFAULT_PROVIDERS))

        providers = [ p.lower() for p in providers \
                     if p.lower() in DEFAULT_PROVIDERS ]

        if not providers:
            providers = DEFAULT_PROVIDERS
            self.logger.info('Using default provider list.')
        else:
            self.logger.info('Using the following providers: %s' %(
                ', '.join(providers)
            ))

        provider_configs = {}
        if 'addic7ed' in providers:
            # Addic7ed Support
            a_username = self.get('Addic7edUsername')
            a_password = self.get('Addic7edPassword')

            if not (a_username and a_password):
                self.logger.warning(
                    'Addic7ed provider dropped due to missing credentials',
                )
                providers.remove('addic7ed')
            else:
                provider_configs['addic7ed'] = {
                    'username': a_username,
                    'password': a_password,
                }

        if not len(providers):
            self.logger.error('There were are no remaining providers to search.')
            return False

        lang = self.parse_list(self.get('Languages', 'en'))
        if not lang:
            self.logger.error('No valid language was set')
            return False

        hearing_impaired = self.parse_bool(
            self.get('HearingImpaired', DEFAULT_HEARING_IMPAIRED))

        if not lang:
            self.logger.error('No valid language was set')
            return False

        try:
            lang = set( babelfish.Language.fromietf(l) for l in lang )
        except babelfish.Error:
            self.logger.error('An error occured processing the language list')

        # Configure cache
        cache_region.configure(
            'dogpile.cache.dbm',
            expiration_time=timedelta(days=30),
            arguments={'filename': cache_file, 'lock_factory': MutexLock},
        )

        # initialize fetch counter
        f_count = 0

        for entry in files:
            if True in [ v.match(entry) is not None \
                        for v in IGNORE_FILELIST_RE ]:
                self.logger.debug('Skipping - Ignored file: %s' % basename(entry))
                continue

            full_path = entry
            if search_mode == SEARCH_MODE.BASIC:
                full_path = join(cache_dir, basename(entry))

            # Create a copy of the lang object
            _lang = set(lang)
            for l in lang:
                # Check that file doesn't already exist
                srt_path = dirname(entry)
                srt_file = basename(splitext(entry)[0])
                srt_file_re = re.escape(srt_file)
                srt_lang = str(l)
                srt_regex = '^(%s\.srt|%s\.%s.srt)$' % (
                    srt_file_re, srt_file_re, srt_lang
                )

                # look in the directory and extract all matches
                _matches = self.get_files(
                    search_dir=srt_path,
                    regex_filter=srt_regex,
                    max_depth=1,
                )
                if not overwrite and len(_matches):
                    self.logger.info(
                        'Skipping - Subtitles already exist for: %s' % (
                            srt_file,
                    ))
                    _lang.remove(l)
                    continue

            if len(_lang) == 0:
                continue

            self.logger.debug('Scanning [%s] using %s lang=%s' % (
                search_mode,
                full_path,
                ', '.join([ str(l) for l in _lang ]),
            ))

            # Scan videos
            videos = scan_videos(
                [full_path, ],
                subtitles=not overwrite,
                embedded_subtitles=not overwrite,
                age=None,
            )

            # Add Guessed Information
            videos.extend([
                Video.fromguess(
                    split(entry)[1],
                    self.guess_info(
                        entry,
                        shared=shared,
                        deobfuscate=deobfuscate,
                        use_nzbheaders=use_nzbheaders,
                    ))
            ])

            subtitles = {}
            if videos:
                # download best subtitles
                subtitles = download_best_subtitles(
                    videos,
                    lang,
                    providers=providers,
                    provider_configs=provider_configs,
                    single=single_mode,
                    min_score=None,
                    hearing_impaired=hearing_impaired,
                )
            else:
                continue

            if not subtitles:
                self.logger.warning('No subtitles were found.')
                continue

            self.logger.info('Matched %d possible subtitle(s) for %s' % \
                (sum([len(s) for s in subtitles.itervalues()]),
                 basename(entry)),
            )
            for res in subtitles.itervalues():
                for sub in res:
                    self.logger.debug('Subtitle found at: %s', str(sub))

            for l in _lang:
                srt_path = abspath(dirname(entry))
                srt_file = basename(splitext(entry)[0])
                srt_lang = str(l)

                if single_mode:
                    expected_file = join(srt_path, '%s.srt' % srt_file)

                else:
                    expected_file = join(srt_path, '%s.%s.srt' % (
                        srt_file, srt_lang,
                    ))

                self.logger.debug('Expecting .srt: %s' % expected_file)

                # Provide other possible locations (unique list)
                potential_files = list(set([ \
                    f for f in [
                        join(abspath(getcwd()), basename(expected_file)),
                        join(cache_dir, basename(expected_file)),
                    ] if isfile(f) and f != expected_file
                ]))

                if self.debug:
                    # Helpful information
                    for potential in potential_files:
                        self.logger.debug(
                            'Potential .srt: %s' % potential
                        )

                if isfile(expected_file):
                    # File was found in the same folder as the movie is
                    # no change is nessisary
                    pass

                elif len(potential_files):
                    # Pop the first item from the potential list
                    while len(potential_files):
                        move_from = potential_files.pop()
                        self.logger.debug(
                            'Expected not found, retrieving: %s' % move_from,
                        )

                        try:
                            # Move our file
                            move(move_from, expected_file)

                            # Move our fetched file to it's final destination
                            self.logger.info('Successfully placed %s' % \
                                             basename(expected_file))
                            # leave loop
                            break

                        except OSError, e:
                            self.logger.error(
                                'Could not move %s to %s' % (
                                    basename(move_from),
                                    expected_file,
                                )
                            )
                            self.logger.debug(
                                'move() exception: %s' % str(e),
                            )

                # Remove any lingering potential files
                try:
                    expected_stat = stat(expected_file)
                except OSError:
                    # weird, expected file was not found..
                    expected_stat = ()

                while len(potential_files):
                    f = potential_files.pop()
                    try:
                        if stat(f) != expected_stat:
                            # non-linked files... proceed
                            unlink(f)
                            self.logger.debug(
                                'Removed lingering extra: %s' % \
                                f,
                            )
                    except:
                        pass

                if not isfile(expected_file):
                    # We can't find anything
                    self.logger.error(
                        'Could not locate subtitle previously fetched!',
                    )
                    continue

                # increment counter
                f_count += 1

        # When you're all done handling the file, just return
        # the error code that best represents how everything worked
        if f_count > 0:
            return True

        # Nothing fetched, nothing gained or lost
        return None

    def postprocess_main(self, *args, **kwargs):

        if not self.validate(keys=(
            'Single',
            'Providers',
            'SearchMode',
            'Addic7edUsername',
            'Addic7edPassword',
            'HearingImpaired',
            'TvCategories',
            'VideoExtensions',
            'Languages')):

            return False

        # Environment
        video_extension = self.get('VideoExtensions', DEFAULT_EXTENSIONS)


        # Single Mode (don't download language extension)
        single_mode = self.parse_bool(
            self.get('Single', DEFAULT_SINGLE))

        # Build file list
        files = self.get_files(suffix_filter=video_extension).keys()
        return self.subliminal_fetch(
            files,
            single_mode=single_mode,
            deobfuscate=True,
            use_nzbheaders=True,
        )

    def scheduler_main(self, *args, **kwargs):

        if not self.validate(keys=(
            'MaxAge',
            'Single',
            'Providers',
            'SearchMode',
            'Addic7edUsername',
            'Addic7edPassword',
            'HearingImpaired',
            'ScanDirectories',
            'VideoExtensions',
            'Languages')):

            return False

        # Environment
        video_extension = self.get('VideoExtensions', DEFAULT_EXTENSIONS)
        maxage = int(self.get('MaxAge', DEFAULT_MAXAGE))
        paths = self.parse_path_list(self.get('ScanDirectories'))

        # Single Mode (don't download language extension)
        single_mode = self.parse_bool(
            self.get('Single', DEFAULT_SINGLE))

        files = self.filter_files_by_age(
            self.get_files(paths, suffix_filter=video_extension).keys(),
            maxage,
        )
        if files:
            self.logger.info('Found %d matched file(s).' % len(files))
            return self.subliminal_fetch(
                files,
                single_mode=single_mode,
                shared=False,
                deobfuscate=False,
                use_nzbheaders=False,
            )
        else:
            self.logger.info('There were no files found.')
            return None

    def main(self, *args, **kwargs):
        """CLI
        """
        # Environment
        video_extension = self.get('VideoExtensions', DEFAULT_EXTENSIONS)
        maxage = int(self.get('MaxAge', DEFAULT_MAXAGE))
        force = self.get('Force', DEFAULT_FORCE)
        paths = self.parse_path_list(self.get('ScanDirectories'))
        single_mode = self.parse_bool(
            self.get('Single', DEFAULT_SINGLE))

        # Fetch Scan Paths
        files = self.get_files(paths, suffix_filter=video_extension).keys()
        if not files:
            self.logger.info('There were no files found.')
            return True
        else:
            self.logger.info('Found %d matched file(s).' % len(files))

        self.logger.debug('Scanning "%s"' %  '","'.join(files))

        if not force:
            files = self.filter_files_by_age(files, maxage)

        if files:
            return self.subliminal_fetch(
                files,
                single_mode=single_mode,
                shared=False,
                deobfuscate=False,
                use_nzbheaders=False,
            )
        else:
            self.logger.warning(
                'There were no files detected less the %dhr(s) ' % maxage +\
                'in age requiring subtitles.')
            self.logger.info(
                'Try adding --force (-f) to force this downloads.'
            )
            return None


# Call your script as follows:
if __name__ == "__main__":
    from sys import exit
    from optparse import OptionParser

    # Support running from the command line
    parser = OptionParser()
    parser.add_option(
        "-S",
        "--scandir",
        dest="scandir",
        help="The directory to scan against. Note: that by setting this " + \
            "variable, it is implied that you are not running this from " + \
            "the command line.",
        metavar="DIR",
    )
    parser.add_option(
        "-a",
        "--maxage",
        dest="maxage",
        help="The maximum age a file can be to be considered searchable. " + \
             "This value is represented in hours",
        metavar="AGE",
    )
    parser.add_option(
        "-l",
        "--language",
        dest="language",
        help="The language the fetch the subtitles in (en, fr, etc).",
        metavar="LANG",
    )
    parser.add_option(
        "-p",
        "--providers",
        dest="providers",
        help="Specify a list of providers (use comma's as delimiters) to " + \
            "identify the providers you wish to use. The following will " + \
            "be used by default: '%s'" % ','.join(DEFAULT_PROVIDERS),
        metavar="PROVIDER1,PROVIDER2,etc",
    )
    parser.add_option(
        "-s",
        "--single",
        action="store_true",
        dest="single_mode",
        help="Download content without the language code in the subtitle " + \
            "filename.",
    )
    parser.add_option(
        "-b",
        "--basic",
        action="store_true",
        dest="basic_mode",
        help="Do not attempt to parse additional information from the " + \
            "video file. Running in a basic mode is much faster but can " + \
            "make it more difficult to determine the correct subtitle if " + \
            "more then one is matched."
    )
    parser.add_option(
        "-f",
        "--force",
        action="store_true",
        dest="force",
        help="Force a download reguardless of the file age",
    )
    parser.add_option(
        "-o",
        "--overwrite",
        action="store_true",
        dest="overwrite",
        help="Overwrite a subtitle in the event one is already present.",
    )
    parser.add_option(
        "-i",
        "--hearingimpaired",
        action="store_true",
        dest="hearingimpaired",
        help="Attempt to download hearing impaired subtitles first and " + \
            "will use normal ones if this fails.",
    )
    parser.add_option(
        "-U",
        "--addic7ed-username",
        dest="a_username",
        help="You must specify a Addic7ed username if you wish to use " +\
        "them as one of your chosen providers.",
        metavar="USERNAME",
    )
    parser.add_option(
        "-P",
        "--addic7ed-password",
        dest="a_password",
        help="You must specify a Addic7ed password if you wish to use " +\
        "them as one of your chosen providers.",
        metavar="PASSWORD",
    )
    parser.add_option(
        "-L",
        "--logfile",
        dest="logfile",
        help="Send output to the specified logfile instead of stdout.",
        metavar="FILE",
    )
    parser.add_option(
        "-D",
        "--debug",
        action="store_true",
        dest="debug",
        help="Debug Mode",
    )
    options, _args = parser.parse_args()


    logger = options.logfile
    if not logger:
        # True = stdout
        logger = True
    debug = options.debug

    script_mode = None
    scandir = options.scandir
    if scandir:
        # By specifying a scandir, we know for sure the user is
        # running this as a standalone script,

        # Setting Script Mode to NONE forces main() to execute
        # which is where the code for the cli() is defined
        script_mode = SCRIPT_MODE.NONE

    script = SubliminalScript(
        logger=logger,
        debug=debug,
        script_mode=script_mode,
    )

    # We always enter this part of the code, so we have to be
    # careful to only set() values that have been set by an
    # external switch. Otherwise we use defaults or what might
    # already be resident in memory (environment variables).
    _language = options.language
    _maxage = options.maxage
    _single_mode = options.single_mode is True
    _overwrite = options.overwrite is True
    _basic_mode = options.basic_mode is True
    _force = options.force is True
    _providers = options.providers
    _hearingimpaired = options.hearingimpaired

    # Addic7ed Support
    _a_username = options.a_username
    _a_password = options.a_password

    if _maxage:
        try:
            _maxage = str(abs(int(_maxage)))
            script.set('MaxAge', _maxage)
        except (ValueError, TypeError):
            script.logger.error(
                'An invalid `maxage` (%s) was specified.' % (_maxage)
            )
            exit(EXIT_CODE.FAILURE)

    if _overwrite:
        script.set('Overwrite', True)

    if _basic_mode:
        script.set('SearchMode', SEARCH_MODE.BASIC)

    if _single_mode:
        script.set('Single', True)

    if _force:
        script.set('Force', True)

    if _providers:
        script.set('Providers', _providers)

    if _a_username:
        script.set('Addic7edUsername', _a_username)

    if _a_password:
        script.set('Addic7edPassword', _a_password)

    if _language:
        script.set('Languages', _language)

    if _hearingimpaired:
        script.set('HearingImpaired', True)

    if scandir:
        # Set some defaults if they are not already set
        if not _maxage:
            _maxage = DEFAULT_MAXAGE
            script.set('MaxAge', DEFAULT_MAXAGE)

        if not _language:
            # Force defaults if not set
            script.set('Languages', DEFAULT_LANGUAGE)

        # Force generic Video Extensions
        script.set('VideoExtensions', DEFAULT_EXTENSIONS)

        # Finally set the directory the user specified for scanning
        script.set('ScanDirectories', scandir)

    # Attach Subliminal logging to output by connecting to its namespace
    logging.getLogger('subliminal').\
            addHandler(script.logger.handlers[0])
    logging.getLogger('subliminal').\
            setLevel(script.logger.getEffectiveLevel())

    # call run() and exit() using it's returned value
    exit(script.run())
