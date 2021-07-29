#!/usr/bin/env python3
'''
This script processes a specified language and outputs the missing
lines using Google Translate. The missing lines are determined by which
lines are in pl.php but not in the specified lang + ".php".

    Copyright (C) 2021  Jake Gustafson

    This software is subject to the terms of the GNU Public License
    Version 2.1 or higher. The full notice can be found in license.txt
    or if the original is not included with this file then:
    <https://github.com/poikilos/justgetalang/blob/main/license.txt>.


Contributing:
- Always use "raise" or this program's "error" function for output
  unless you are emitting missing php lines.
  - The "print" statement is reserved for emitting php code to standard
    output (See "usage").
'''

usage = '''
-------------------------------- USAGE --------------------------------
This script processes a specified language and outputs the missing
lines using Google Translate. The missing lines are determined by which
lines are in {original_lang}.php but not in the specified target
language + ".php".

Specify a language that exists in the {lang} directory under the
current directory.

Example:
  python3 justgetalang.py en
'''


import os
import sys
import json
import platform

verbose = True

trCache = {}
trCachePath = 'trCache.json'
if os.path.isfile(trCachePath):
    with open(trCachePath) as ins:
        trCache = json.load(ins)

def _translate(value, fromLang, toLang):
    '''
    Translate value to toLang.
    '''
    debug("  *translate chunk* " + value)
    return value

builtins_en_done = {}

def build_builtins_en(fromLang, toLang):
    '''
    Forcibly copy English words found in a non-english source
    to the destination language.

    Sequential arguments:
    fromLang -- This is the language of the source that has mixed in
                English words.
    toLang -- This is the destination language. Since this function
              overwrites parts with English, toLang should be en,
              en_US, en_GB or some other English dialect.
    '''
    if trCache.get(fromLang) is None:
        trCache[fromLang] = {}
    if trCache[fromLang].get(toLang) is None:
        trCache[fromLang][toLang] = {}
    # The game-related
    andrzuk_games = [
        'Demo',
        'Score:',
        'Scores List',
        'Speed:',
        'Super fast (20x)',
        'Very fast (10x)',
        'Faster (5x)',
        'Little faster (4x)',
        'Medium (3x)',
        'Slow (2x)',
        'Very slow (1x)',
        'Play',
        'Pause',
        'Map editor',
        'Canvas is not supported in your browser.',
        'Start',
        'Keyboard control:',
        'Rotation:',
        'PageUp',
        'PageDown',
        'Move:',
        'Left',
        'Right',
        'Down',
        'Drop:',
        'Space bar',
        'Space Bar',
        'Save &amp; Exit',
        'Save &amp; exit',
        'Close',
        'Tetris Maps Editor',
        '-180 days',
    ]
    for same in andrzuk_games:
        trCache[fromLang][toLang][same] = same

    sames = [
        'http',
        'https',
        'Mail Manager',
    ]
    # TODO: Handle sub-parts such as in "-180 days"
    # TODO: handle different capitalization and preserve case.
    for same in sames:
        trCache[fromLang][toLang][same] = same

    builtins_en_done[fromLang] = True

def translateCached(value, fromLang, toLang):
    rawV = value
    value = value.lstrip()
    preSpace = rawV[:len(rawV)-len(value)]
    postSpace = ""
    postSpaceLen = len(rawV) - len(rawV.rstrip())
    if postSpaceLen > 0:
        postSpace = rawV[-postSpaceLen:]
    value = value.rstrip()
    if trCache.get(fromLang) is None:
        trCache[fromLang] = {}
    if trCache[fromLang].get(toLang) is None:
        trCache[fromLang][toLang] = {}
    if (toLang == "en") or (toLang.startswith("en_")):
        if not builtins_en_done.get(fromLang) is True:
            build_builtins_en(fromLang, toLang)
    got = trCache[fromLang][toLang].get(value)
    if got is None:
        got = _translate(value, fromLang, toLang)
        # trCache[fromLang][toLang][value] = got
    return preSpace + got + postSpace

class DirtyHTML:
    FMT_HTML = 'html'
    FMT_TEXT = 'text'
    FMT_CSS = 'css'

    def __init__(self, value, fmt):
        '''
        Sequential arguments:
        value -- any string
        fmt -- a format describing the string (It must match one of the
               DirtyHTML.FMT_ constants.
        '''
        self.value = value
        self.fmt = fmt


class ParseDirtyHTML:
    '''
    This is an iterator that either gives you an html chunk (a
    DirtyHTML object where o.fmt describes the language
    on each iteration (See DirtyHTML.FMT_ constants for possible
    values of o.fmt).
    Iterate through one of these to process your
    html in a blunt manner even if the quotes inside of tags are
    escaped (such as ones stored with the dreaded "magic quotes").

    For certainty despite the assumptions, the iterator will
    raise a SyntaxError if there is any closing sign ('>') before an
    opening sign ('<'), or there is another opening sign before an
    opened tag is closed by a closing sign.

    The only exception is when the signs are in a style tag--in that
    case, everything will be taken as html

    This was made for processing language strings in
    Poikilos/AngularCMS's internationalization branch, but it can do
    pretty much anything that requires the assumptions above.
    '''

    def __init__(self, data, path, lineN, offset):
        '''
        Sequential arguments:
        data -- Any parts enclosed in '<' and '>' are considered to be
                HTML tags no matter how messy everything else is.
        path -- The file path, if any, only used for error messages.
        lineN -- The line number, if any, only used for error messages.
        offset -- The column number at which the data starts in the
                  source code, only used for error messages.
        '''
        self._data = data
        self._i = 0  # This is the position in data.
        self._start = 0  # This is the start of the chunk.
        self._in_fmt = 'text'
        self.path = path
        self.lineN = lineN
        if offset is None:
            offset = -1
        self.offset = offset

    def __iter__(self):
        return self

    @staticmethod
    def isSubdirectory(s):
        '''
        Determine True or False: whether s is a subdirectory such as
        starting with "/" or "\\" rather than a regular language string.
        '''
        s = s.strip()
        if s.startswith("/"):
            return True
        if s.startswith("\\"):
            return True
        return False

    @staticmethod
    def isEmail(s, allow_local=False):
        '''
        Determine True or False: whether s is an e-mail address
        such as with characters then '@' and then characters;
        and no spaces.

        Keyword arguments:
        allow_local -- Allow the address to have only characters and
                       not any dot after the '@'
        '''
        s = s.strip()
        if " " in s:
            return False
        atI = s.find('@')
        if atI < 1:
            # ^ must be after 0
            return False
        if not allow_local:
            dotI = s.find('.', atI)
            if dotI <= atI + 1:
                # The dot is directly after the '@'.
                return False
            elif dotI == (len(s) - 1):
                # It ends with dot.
                return False
            return True
        elif len(s) < atI + 1:
            return False
        else:
            return True

    @staticmethod
    def isMention(s):
        '''
        Determine True or False: whether s is an @ mention
        (starts with '@' and has no spaces)
        '''
        s = s.strip()
        if " " in s:
            return False
        if s[0:1] == '@':
            return True
        return False

    @staticmethod
    def isHashtag(s):
        '''
        Determine True or False: whether s is a '#' hashtag
        (starts with '#' and has no spaces)
        '''
        s = s.strip()
        if " " in s:
            return False
        if s[0:1] == '#':
            return True
        return False

    @staticmethod
    def isMoney(s, symbol, symbolGoesAtEnd):
        '''
        Determine True or False: whether s is a dollar value.
        '''
        s = s.strip()
        if not symbolGoesAtEnd:
            if not s.startswith(symbol):
                return False
        else:
            if not s.endswith(symbol):
                return False
        return ParseDirtyHTML.isNumber(s[1:])

    @staticmethod
    def isPunctuation(s):
        '''
        Determine True or False: whether s is only punctuation or blank.
        '''
        s = s.strip()
        for c in s:
            if c.isalpha():
                return False
        return True


    @staticmethod
    def isCodeSimpleAssignmentOp(s):
        '''
        Determine True or False: whether s is a simple assignment
        operation such as "gameInterval = null;" (with or without a
        semicolon, but with no spaces in either of the 2 parts!)
        '''
        s = s.strip()
        parts = s.split("=")
        if len(parts) == 2:
            if ' ' not in parts[0].strip():
                if ' ' not in parts[1].strip():
                    return True
        return False


    @staticmethod
    def isNumber(s):
        '''
        Determine True or False: whether s is a numeric string.
        '''
        # NOTE: If it starts with '-' or has '.' then
        # s.isnumeric() returns False!
        s = s.strip()
        try:
            tmp = int(s)
            return True
        except ValueError:
            try:
                tmp = float(s)
                return True
            except ValueError:
                return False
        return False

    @staticmethod
    def isDomainLike(s):
        '''
        Determine True or False: whether s is potentially a local or
        online domain name (has a '.' and has no spaces)
        '''
        s = s.strip()
        if ParseDirtyHTML.isNumber(s):
            return False
        if ' ' in s:
            return False
        if '.' in s:
            return True
        return False

    def __next__(self):
        data = self._data
        styleOpeners = ["<style ", "<style>"]
        styleCloser = "</style>"
        if self._i >= len(data):
            raise StopIteration
        while self._i < len(data):
            if self._in_fmt == DirtyHTML.FMT_HTML:
                if data[self._i] == "<":
                    prefix = "{}:{}:{}: ".format(self.path, self.lineN,
                                                 self._i+self.offset)
                    msg = ("An opening bracket"
                           " occurred before the previous one"
                           " was closed in \"{}\""
                           "".format(data))
                    error(prefix)
                    # ^ Don't show the location using "SyntaxError",
                    #   since that would put "SyntaxError: " before it.
                    raise SyntaxError(msg)
                if data[self._i] == ">":
                    start = self._start
                    self._i += 1
                    self._start = self._i
                    # ^ Get start after incrementing since closing.
                    self._in_fmt = 'text'
                    for styleOpener in styleOpeners:
                        ender = start+len(styleOpener)
                        if data[start:ender].lower() == styleOpener:
                            self._in_fmt = 'css'
                    return DirtyHTML(data[start:self._i],
                                     DirtyHTML.FMT_HTML)
                    # ^ Use the incremented _i since the character
                    #   before it is the closer and is part of the
                    #   html chunk.
            elif self._in_fmt == DirtyHTML.FMT_TEXT:
                if data[self._i] == ">":
                    prefix = "{}:{}:{}: ".format(self.path, self.lineN,
                                                 self._i+self.offset)
                    msg = ("A closing bracket occurred"
                           " before an opening bracket"
                           " in \"{}\""
                           "".format(data))
                    error(prefix)
                    # ^ Don't show the location using "SyntaxError",
                    #   since that would put "SyntaxError: " before it.
                    raise SyntaxError(msg)
                if data[self._i] == "<":
                    self._in_fmt = 'html'
                    if (self._i - self._start) > 0:
                        start = self._start
                        self._start = self._i
                        # ^ Get start before incrementing since opening.
                        self._i += 1
                        return DirtyHTML(data[start:self._i-1],
                                         DirtyHTML.FMT_TEXT)
                        # ^ Use the previous start. Go back one since
                        #   the new opener is not part of the previous
                        #   non-html chunk.
                    # else the string starts with a tag, so keep going
                    # until there is something to return.
            elif self._in_fmt == DirtyHTML.FMT_CSS:
                ender = self._i+len(styleCloser)
                if data[self._i:ender].lower() == styleCloser:
                    start = self._start
                    self._start = self._i
                    # ^ Start the closing style tag at the '<'.
                    self._in_fmt = DirtyHTML.FMT_HTML
                    self._i += 1
                    return DirtyHTML(data[start:self._i-1],
                                     DirtyHTML.FMT_CSS)
                    # ^ This is technically a closing of css even though
                    #   it is an opening of html, so go back by -1
                    #   to avoid capturing the '<' in styleCloser.
            else:
                raise RuntimeError("The parser is in an invalid state:"
                                   " self._in_fmt={}"
                                   "".format(value_to_py(self._in_fmt)))
            self._i += 1

        start = self._start
        self._start = self._i
        if self._in_fmt != DirtyHTML.FMT_TEXT:
            prefix = "{}:{}:{}: ".format(self.path, self.lineN,
                                         start+self.offset)
            error(prefix)
            raise SyntaxError("The line ends without closing the"
                              "{} tag that starts here."
                              "".format(self._in_fmt))
        if (self._i - start) > 0:
            return DirtyHTML(data[start:self._i], self._in_fmt)
        else:
            raise StopIteration


def value_to_py(v, q='"'):
    '''
    Convert a value to a Python RValue ready to save to a py file.

    Sequential arguments:
    v -- the value of any type in its usable form

    Keyword arguments:
    q -- what quote mark to use on the value
    '''
    if v is None:
        return "None"
    elif v is True:
        return "True"
    elif v is False:
        return "False"
    try:
        tmp = v.strip()
        # ^ If there is no AttributeError, assume it is a string.
        v = v.replace(q, "\\"+q)  # Escape the quotes.
        return q + v + q
    except AttributeError:
        if isinstance(v, (int, float)):
            return v
        return repr(v)


def set_verbose(v):
    '''
    Set whether to show verbose output.
    This function requires value_to_py.

    Sequential arguments:
    v -- True for on, False for no output from the debug function.
    '''
    if v is True:
        verbose = True
    elif v is False:
        verbose = False
    else:
        raise ValueError("You must specify True or False (got {})."
                         "".format(value_to_py(v)))

def error(msg):
    sys.stderr.write(msg + "\n")

def debug(msg):
    if not verbose:
        return
    sys.stderr.write(msg + "\n")

try:
    import googletrans
except ModuleNotFoundError:
    print("You must install googletrans such as via:")
    print("python3 -m pip install --user googletrans")
    exit(1)

from googletrans import Translator


error("googletrans.LANGUAGES: " + json.dumps(googletrans.LANGUAGES))
error("")

origLang = "pl"
profile = None
if platform.system() == "Windows":
    profile = os.environ['USERPROFILE']
else:
    profile = os.environ['HOME']
reposPath = os.path.join(profile, "git")
tryPath = os.path.join(reposPath, "AngularCMS")

repoPath = os.path.dirname(os.path.realpath(__file__))
if os.path.isdir(tryPath):
    error("INFO: The path is automatically changing"
          " from \"{}\" to the detected \"{}\"."
          "".format(repoPath, tryPath))
    repoPath = tryPath
langsPath = os.path.join(repoPath, "lang")


def usage():
    error(usage.format(
        lang=langPath,
        original_lang=origLang,
    ))


ignores = ["translations.php"]


spacing_chars = " \t\n\r\f\v"


def find_non_whitespace(haystack, start):
    '''
    Get the next non-whitespace character at or after start.
    This function requires the global spacing_chars.

    Sequential arguments:
    haystack -- Search this string.
    start -- Start at this index in haystack.
    '''
    i = start

    while i < len(haystack):
        if haystack[i] not in spacing_chars:
            return i
        i += 1
    return -1


def find_quoted_not_escaped(haystack, *args):
    '''
    Get the quoted portion excluding the quotes,
    ignoring escaped quotes of that kind.

    Example:

    code_line = "d['some_key']"
    found = find_quoted_not_escaped(code_line)
    if found[1] > -1:
        key = code_line[found[0]:found[1]]
        quote = found[2]
        # The value of key is now "some_key", excluding the quotes.
    elif found[0] > -1:
        print("The closing {} wasn't found in \"{}\"."
              "".format(found[2], code_line))

    Sequential arguments:
    haystack -- Find the quote in this.
    start -- (optional) Start at this index in haystack.

    Returns:
    a tuple of the slice values of haystack in quotes not including
    the quotes, then the quote mark used;
    or if not found: (-1, -1, None). Check to make sure the second
    value isn't -1 before using the values.
    '''
    start = 0
    if haystack is None:
        raise ValueError("You must at least specify a string.")
    if len(args) > 1:
        raise ValueError("You can only specify a string and a start.")
    if len(args) == 1:
        start = args[0]

    i = start
    openQI = -1
    closeQI = -1

    enclosures = {}
    enclosures["'"] = "'"
    enclosures['"'] = '"'
    closing = None
    prevChar = ""

    while i < len(haystack):
        if closing is None:
            if haystack[i] in enclosures.keys():
                closing = enclosures[haystack[i]]
                openQI = i
        else:
            if (haystack[i] == closing) and (prevChar != "\\"):
                closeQI = i
                return (openQI+1, closeQI, closing)
        prevChar = haystack[i]
        i += 1
    return (openQI, -1, closing)


class JGALPhraseBuilder:
    def __init__(self):
        self.lineN = 0
        self.vCol = 0

    def build(self):
        return JGALPhrase(self)

class JGALPhrase:
    '''
    Track the context of a translated phrase within a code file.
    '''

    def __init__(self, builder):
        '''
        Required builder members:
        key -- the key in this language
        value -- the phrase in the particular language
        gQ -- the quote symbol used around the key directly in globals
        lQ -- the quote symbol used around the language
        kQ -- the quote symbol used around the key on this line
        vQ -- the quote symbol used around the value on this line
        extras -- any lines that occur before this line in the file
        indent -- anything before the line starts such as spacing
        suffix -- a semicolon (not required), comments, or anything else
                  after the closing bracket

        Optional members:
        lineN -- the source code line number only used for errors
        vCol -- the source code column at which the value starts
        '''
        self.lang = builder.lang
        self.key = builder.key
        self.value = builder.value
        self.gQ = builder.gQ
        self.lQ = builder.lQ
        self.kQ = builder.kQ
        self.vQ = builder.vQ
        self.extras = builder.extras
        self.indent = builder.indent
        self.suffix = builder.suffix
        self.globalsName = builder.globalsName
        self.translationsKey = builder.translationsKey
        self.langDotExt = builder.langDotExt
        self.lineN = builder.lineN
        self.vCol = builder.vCol

    def reconstruct(self, lang, value):
        '''
        Use this phrase as a template and return a new JGALPhrase
        with the new language and value specified.
        '''
        builder = JGALPhraseBuilder()
        builder.lang = lang
        builder.key = self.key
        builder.value = value
        builder.gQ = self.gQ
        builder.lQ = self.lQ
        builder.kQ = self.kQ
        builder.vQ = self.vQ
        builder.extras = self.extras
        builder.indent = self.indent
        builder.suffix = self.suffix
        builder.globalsName = self.globalsName
        builder.translationsKey = self.translationsKey
        builder.langDotExt = self.langDotExt
        builder.lineN = self.lineN
        return builder.build()

    def toCode(self):
        '''
        Convert this back to the original language that originated it,
        including the indent and the suffix (which would include a
        semicolon if the line in the original program did).
        '''
        return (self.indent + self.globalsName + '[' + self.gQ +
                self.translationsKey + self.gQ + ']['
                + self.lQ + self.lang + self.lQ + ']['
                + self.kQ + self.key + self.kQ + '] = '
                + self.vToPy(self.value) + self.suffix)

    def gToPy(self, s):
        '''
        Return a quoted and escaped version of s using
        this variable's line's translations global quote mark.

        This method requires value_to_py.
        '''
        return value_to_py(str(s), q=self.gQ)

    def lToPy(self, s):
        '''
        Return a quoted and escaped version of s using
        this variable's line's quote mark that was around the language.

        This method requires value_to_py.
        '''
        return value_to_py(str(s), q=self.lQ)

    def kToPy(self, s):
        '''
        Return a quoted and escaped version of s using
        this variable's line's quote mark that was around the key.

        This method requires value_to_py.
        '''
        return value_to_py(str(s), q=self.kQ)

    def vToPy(self, s):
        '''
        Return a quoted and escaped version of s using
        this variable's line's quote mark that was around the key.

        This method requires value_to_py.
        '''
        return value_to_py(str(s), q=self.vQ)


class JGALPack:

    existingLangsWarn = True
    default_globalsName = '$GLOBALS'
    default_translationsKey = 'translations'
    default_langDotExt = ".php"
    CO = 0  # Set this to 1 if 1st column is 1 in your code editor.

    def getPath(self):
        return os.path.join(self.langs_path, self.lang + self.dotExt)

    def __init__(self, langs_path, sub, lang,
                 globalsName=None,
                 translationsKey=None):
        '''
        Sequential arguments:
        langs_path -- This must contain the language file named sub.
        sub -- This language file must be in langs_path.
        lang -- This language must be a valid language id string such
                as recognized by Google Translate. It is used as the
                key within the translations associative array.

        Keyword arguments:
        globalsName -- the name of the globals object in your code, such
                       as $GLOBALS
        translationsKey -- the key in the globals that accesses the
                           entire translations associative array
        '''
        if globalsName is None:
            globalsName = JGALPack.default_globalsName
        self.globalsName = globalsName
        if translationsKey is None:
            translationsKey = JGALPack.default_translationsKey
        self.translationsKey = translationsKey
        self.phrases = {}
        self.keys = []  # This list exists to keep the keys in order.
        translationsSymbol = "{}[".format(globalsName)
        # The full opening is: translationsSymbol
        #                      + "['"+translationsKey+"']"
        # but they can be either single quotes or double quotes, so
        # search for them.
        if not sub.lower().endswith(".php"):
            error("  * Warning in {}: only PHP is known for sure."
                  " The format that is required"
                  " (and that will be attempted anyway) is:"
                  " {}['key'] = 'value'"
                  " (where a single or"
                  " double quote is allowed"
                  " and the line may or may not end with a semicolon"
                  " and/or comment)"
                  "".format(translationsSymbol, lang))
        self.dotExt = os.path.splitext(sub)[1]
        self.langs_path = langs_path
        self.sub = sub
        if not os.path.isdir(langs_path):
            raise ValueError("Error: langs_path \"{}\" is missing."
                             "".format(langs_path))
        self.path = os.path.join(langs_path, sub)
        if not os.path.isfile(self.path):
            raise ValueError("Error: self.path \"{}\" is not a file."
                             "".format(self.path))
        self.lang = lang
        count = 0
        lineN = 0
        CO = JGALPack.CO
        with open(self.path) as ins:
            extras = []
            for rawL in ins:
                lineN += 1
                line = rawL.strip()
                spacingLen = len(line) - len(line.lstrip())
                indent = line[:spacingLen]
                inLine = line.rstrip("\n\r\f")
                if not line.startswith(translationsSymbol):
                    debug("[verbose] Doesn't start with \"{}\": \"{}\""
                          "".format(translationsSymbol, line))
                    extras.append(inLine)
                    continue
                count += 1
                preGlobalI = len(translationsSymbol)

                gFound = find_quoted_not_escaped(line, preGlobalI)
                # ^ The global key in globals may be found at this slice
                #   using quote gFound[2].
                if gFound[1] < 0:
                    if gFound[0] > -1:
                        error("{}:{}:{}: The closing {} around the"
                              " translations key after the opening"
                              " {} was missing."
                              "".format(self.path, lineN, gFound[0]+CO,
                                        gFound[2], line[gFound[0]-1]))
                    extras.append(inLine)
                    continue

                debugStr = line[gFound[0]:gFound[1]]
                if debugStr != translationsKey:
                    error("{}:{}:{}: WARNING: expected"
                          " the key {} in {}."
                          "".format(self.path, lineN, kFound[0]+CO,
                                    translationsKey,
                                    translationsSymbol))
                    extras.append(inLine)
                    continue
                firstCBI = find_non_whitespace(line, gFound[1]+1)
                # ^ the first closing bracket's index
                # if line[firstCBI] != "]":
                if (firstCBI < 0) or (line[firstCBI]!="]"):
                    error("{}:{}:{}: A closing bracket is expected"
                          "after the quoted translations key."
                          "".format(self.path, lineN, gFound[1]+1+CO))
                    extras.append(inLine)
                    continue
                preLangI = firstCBI + 1
                if (preLangI >= len(line)) or (line[preLangI]!="["):
                    error("{}:{}:{}: An opening bracket is expected"
                          " after the close bracket after"
                          " the translations key."
                          "".format(self.path, lineN, preLangI+CO))
                    extras.append(inLine)
                    continue

                lFound = find_quoted_not_escaped(line, preLangI)

                if lFound[1] < 0:
                    if lFound[0] > -1:
                        error("{}:{}:{}: WARNING: The closing {}"
                              " around the language after the opening"
                              " {} was missing. Maybe it is the"
                              " declaration of {}['{}']"
                              "".format(self.path, lineN, lFound[0]+CO,
                                        lFound[2], line[lFound[0]-1],
                                        translationsSymbol,
                                        translationsKey))
                    extras.append(inLine)
                    continue
                debugLang = line[lFound[0]:lFound[1]]
                if debugLang != lang:
                    error("{}:{}:{}: ERROR: The lang '{}' was expected"
                          " but the line specifies '{}'."
                          "".format(self.path, lineN, lFound[0]+CO,
                                    lang,
                                    debugLang))
                    extras.append(inLine)
                    continue

                keyCBI = find_non_whitespace(line, lFound[1]+1)
                if (keyCBI < 0) or (line[keyCBI]!="]"):
                    error("{}:{}:{}: A closing bracket is expected"
                          "after the quoted language."
                          "".format(self.path, lineN, lFound[1]+1+CO))
                    extras.append(inLine)
                    continue

                preKeyI = keyCBI + 1

                kFound = find_quoted_not_escaped(line, preKeyI)
                # ^ The key may be found at this slice
                #   using quote kFound[2].
                if kFound[1] < 0:
                    if kFound[0] > -1:
                        error("{}:{}:{}: WARNING: The closing {}"
                              " around the key after the opening"
                              " {} was missing. Maybe it is the"
                              " declaration of {}['{}']"
                              "".format(self.path, lineN, kFound[0]+CO,
                                        kFound[2], line[kFound[0]-1],
                                        translationsSymbol,
                                        translationsKey))
                    extras.append(inLine)
                    continue

                key = line[kFound[0]:kFound[1]]
                # debug("key:{}".format(key))
                # ^ The value of key is now "some_key" excluding quotes.
                keyQ = kFound[2]
                closeBI = find_non_whitespace(line, kFound[1] + 1)
                # ^ closeBI is the closing bracket's index for
                #   The key.
                # if kFound[1] + 3 >= len(line):
                if closeBI < 0:
                    error("{}:{}:{}: The line ended after the key"
                          " but before the value."
                          "".format(self.path, lineN, kFound[1]+CO))
                if line[closeBI] != "]":
                    error("{}:{}:{}: A closing bracket was expected."
                          "".format(self.path, lineN, closeBI+CO))
                signI = find_non_whitespace(line, closeBI+1)
                # if (closeBI+1>=len(line)) or (line[closeBI+1] != "="):
                if (signI < 0) or (line[signI] != "="):
                    error("{}:{}:{}: '=' was expected after ']'"
                          " but got \"{}\"."
                          "".format(self.path, lineN, closeBI+1+CO,
                                    line[closeBI+1:]))
                vFound = find_quoted_not_escaped(line, signI+1)
                if vFound[1] < 0:
                    if vFound[0] > -1:
                        error("{}:{}:{}: The closing {}"
                              " around the value after the opening"
                              " {} was missing."
                              "".format(self.path, lineN, signI+1+CO,
                                        vFound[2], line[vFound[0]]))
                        extras.append(inLine)
                        continue
                    error("{}:{}:{}: The opening quote"
                          " for the value after "
                          " '{}' was missing."
                          "".format(self.path, lineN, signI+1+CO,
                                    line[signI]))
                    extras.append(inLine)
                    continue
                rawV = line[vFound[0]:vFound[1]]
                value = rawV.replace("\\"+vFound[2], vFound[2])
                debug("{}:{}:{}: [verbose] got: ['{}']['{}']['{}']={}"
                      "".format(self.path, lineN, signI+CO,
                                debugStr, debugLang, key,
                                value_to_py(value, q="'")))
                suffix = ""
                lastCBI = find_non_whitespace(line, vFound[1]+1)
                if lastCBI > -1:
                    suffix = line[lastCBI+1:]
                else:
                    error("{}:{}:{}: ']' was expected after the key."
                          "".format(self.path, lineN, vFound[1]+1+CO))
                # ^ the last closing bracket's index
                builder = JGALPhraseBuilder()
                builder.lang = debugLang
                builder.key = key
                builder.value = value
                builder.gQ = gFound[2]
                builder.lQ = lFound[2]
                builder.kQ = kFound[2]
                builder.vQ = vFound[2]
                builder.extras = extras
                builder.indent = indent
                builder.suffix = suffix
                builder.globalsName = self.globalsName
                builder.translationsKey = self.translationsKey
                builder.langDotExt = self.dotExt
                builder.lineN = lineN
                builder.vCol = vFound[0] + CO
                phrase = builder.build()

                self.phrases[key] = phrase
                self.keys.append(key)
                extras = []
                indent = None
                suffix = None

        error("INFO: JGALPack init processed {} line(s)"
              " in \"{}\" that started with \"{}\" and got"
              " {} phrase(s)"
              "".format(count, self.path, translationsSymbol,
                        len(self.keys)))

    @classmethod
    def existingLangs(cls, ignore_langs=None):
        dirs = list(os.listdir(langsPath))
        langs = []
        for d in dirs:
            dPath = os.path.join(langsPath, d)
            if not os.path.isfile(dPath):
                continue
            if d in ignores:
                continue
            if not d.lower().endswith(cls.default_langDotExt.lower()):
                if cls.existingLangsWarn:
                    print("WARNING: list langs ignored the file \"{}\""
                          " since it is not a {} file."
                          "".format(d, cls.default_langDotExt))
                continue
            if ignore_langs is not None:
                if d in ignore_langs:
                    continue
            langs.append(d[:-len(cls.default_langDotExt)])
        cls.existingLangsWarn = False
        return langs

escaped = {}
escaped["\\'"] = "'"
escaped["\\\""] = "\""
escaped["\\a"] = "\a"
escaped["\\b"] = "\b"
escaped["\\f"] = "\f"
escaped["\\n"] = "\n"
escaped["\\t"] = "\t"
escaped["\\v"] = "\v"


def escape_only(s, seq):
    '''
    Replace instances of the real meaning of the sequence with seq
    and return the result.

    Sequential arguments:
    s -- any string
    c -- a valid python escape character
    '''
    got = escaped.get(seq)
    if got is None:
        raise ValueError("\"{}\" is not an implemented escape"
                         " sequence.".format(seq))
    return s.replace(got, seq)


def unescape_only(s, seq):
    '''
    Replace instances of seq with the real meaning
    and return the result.

    Sequential arguments:
    s -- any string
    c -- any pair (escape sequence)

    '''
    got = escaped.get(seq)
    if got is None:
        raise ValueError("\"{}\" is not an implemented escape"
                         " sequence.".format(seq))
    return s.replace(seq, got)


def main():
    if len(sys.argv) < 2:
        usage()
        error("")
        raise ValueError("Error: You must specify a language to check.")
    nextLang = sys.argv[1]
    langDotExt = JGALPack.default_langDotExt
    origLangSub = origLang + langDotExt
    origLangPath = os.path.join(langsPath, origLangSub)
    if nextLang == origLang:
        langs = existingLangs([origLangSub])
        usage()
        error("")
        raise ValueError("You must specify a language to check, but"
                         " you specified the original language ({})."
                         " You must specify a language such as one "
                         " in \"{}\":"
                         " {}".format(origLang, langsPath, langs))
    nextSub = nextLang + langDotExt
    nextPath = os.path.join(langsPath, nextSub)
    if not os.path.isfile(nextPath):
        usage()
        error("")
        raise ValueError("Error: There is no \"{}\"."
                         " Create it then try again."
                         "".format(nextPath))
    if not os.path.isdir(langsPath):
        usage()
        error("")
        raise RuntimeError("Error: langsPath \"{}\" is missing."
                           "".format(langsPath))
    if not os.path.isfile(origLangPath):
        usage()
        error("")
        raise ValueError("Error: \"{}\" is missing (origLang={},"
                         " langDotExt={})"
                         "".format(origLangPath, origLang,
                                   langDotExt))

    # for nextSub in os.listdir(langsPath):
    #     nextPath = os.path.join(langsPath, nextSub)
    #     if nextSub.startswith("."):
    #         continue
    #     if not os.path.isfile(nextPath):
    #         continue
    #     if nextSub == origLangSub:
    #         continue
    #     error("* analyzing \"{}\"...".format(nextSub))
    #     #result = translator.translate(srcVal)
    # thisDotExt = langDotExt
    if not nextSub.lower().endswith(langDotExt.lower()):
        # continue
        nextLang = os.path.splitext(nextSub)[0]
        # thisDotExt = os.path.splitext(nextSub)[1]
    else:
        nextLang = nextSub[:-len(langDotExt)]

    error("INFO: analyzing \"{}\"...".format(nextPath))
    nextPack = JGALPack(langsPath, nextSub, nextLang)
    error("INFO: analyzing \"{}\"...".format(origLangPath))
    origPack = JGALPack(langsPath, origLangSub, origLang)
    for key in origPack.keys:
        nextPhrase = nextPack.phrases.get(key)
        # ^ See if the original language key is in the target language.
        if nextPhrase is not None:
            # It already is in the target.
            continue
        # nextPhrase is None, so generate it through translation.
        origPhrase = origPack.phrases[key]
        # debug("*translate phrase* {}".format(origPhrase.value))
        nextValue = ""
        for chunk in ParseDirtyHTML(origPhrase.value,
                                    origPack.getPath(),
                                    origPhrase.lineN,
                                    origPhrase.vCol):
            if chunk.fmt != DirtyHTML.FMT_TEXT:
                nextValue += chunk.value
            else:
                escapeQ = None
                tmp = chunk.value
                if "\\\"" in tmp:
                    escapeQ = '"'
                elif "\\'" in tmp:
                    escapeQ = "'"
                if escapeQ is not None:
                    tmp = tmp.replace("\\" + escapeQ, escapeQ)
                tmp = unescape_only(tmp, "\\n")
                formatting = False
                tmpStrip = tmp.strip()
                if len(tmpStrip) < 1:
                    formatting = True
                elif (tmpStrip.startswith("&")
                      and tmpStrip.endswith(";")):
                    formatting = True
                elif ParseDirtyHTML.isSubdirectory(tmpStrip):
                    formatting = True
                elif ParseDirtyHTML.isEmail(tmpStrip):
                    formatting = True
                elif ParseDirtyHTML.isMention(tmpStrip):
                    formatting = True
                elif ParseDirtyHTML.isHashtag(tmpStrip):
                    formatting = True
                elif ParseDirtyHTML.isMoney(tmpStrip, "$", False):
                    formatting = True
                elif ParseDirtyHTML.isPunctuation(tmpStrip):
                    formatting = True
                elif ParseDirtyHTML.isCodeSimpleAssignmentOp(tmpStrip):
                    formatting = True
                elif ParseDirtyHTML.isNumber(tmpStrip):
                    formatting = True
                elif ParseDirtyHTML.isDomainLike(tmpStrip):
                    formatting = True
                if not formatting:
                    tmp = translateCached(tmp, origLang, nextLang)
                    #debug("  *translate chunk* " + tmp)
                tmp = escape_only(tmp, "\\n")
                if escapeQ is not None:
                    tmp = tmp.replace(escapeQ, "\\" + escapeQ)
                nextValue += tmp
        # NOTE: If *translated chunk* does NOT appear above for
        #       any words in the phrase below, then all of the
        #       chunks were (or the singular chunk if no html tags
        #       were present was) determined to be formatting and
        #       not actually translated.
        debug("    *translated phrase* " + nextValue)
        gQ = origPhrase.gQ
        lQ = origPhrase.lQ
        kQ = origPhrase.kQ

        for extra in origPhrase.extras:
            print(extra)
        nextPhrase = origPhrase.reconstruct(nextLang, nextValue)
        print(nextPhrase.toCode())

    with open(trCachePath, 'w') as outs:
        json.dump(trCache, outs, sort_keys=True, indent=2)
    error("INFO: The cache was saved to \"{}\"".format(trCachePath))

if __name__ == "__main__":
    main()

