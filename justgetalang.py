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


class DirtyHTML:
    def __init__(self, value, is_html):
        self.value = value
        self.is_html = is_html


class ParseDirtyHTML:
    '''
    This is an iterator that either gives you an html chunk (a
    DirtyHTML object where o.is_html is True) or
    a text chunk (where o.is_html is false) on each iteration.
    Iterate through one of these to process your
    html in a blunt manner even if the quotes inside of tags are
    escaped (such as ones stored with the dreaded "magic quotes").

    For certainty despite the assumptions, the iterator will
    raise a SyntaxError if there is any closing sign ('>') before an
    opening sign ('<'), or there is another opening sign before an
    opened tag is closed by a closing sign.

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
        self._in_tag = False
        self.path = path
        self.lineN = lineN
        if offset is None:
            offset = -1
        self.offset = offset

    def __iter__(self):
        return self

    def __next__(self):
        data = self._data
        if self._i >= len(data):
            raise StopIteration
        while self._i < len(data):
            if self._in_tag:
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
                    self._in_tag = False
                    return DirtyHTML(data[start:self._i], True)
                    # ^ Use the incremented _i since the character
                    #   before it is the closer and is part of the
                    #   html chunk.
            else:
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
                    self._in_tag = True
                    if (self._i - self._start) > 0:
                        start = self._start
                        self._start = self._i
                        # ^ Get start before incrementing since opening.
                        self._i += 1
                        return DirtyHTML(data[start:self._i-1], False)
                        # ^ Use the previous start. Go back one since
                        #   the new opener is not part of the previous
                        #   non-html chunk.
                    # else the string starts with a tag, so keep going
                    # until there is something to return.
            self._i += 1

        start = self._start
        self._start = self._i
        if self._in_tag:
            prefix = "{}:{}:{}: ".format(self.path, self.lineN,
                                         start+self.offset)
            error(prefix)
            raise SyntaxError("The line ends without closing the"
                              "tag that starts here.")
        if (self._i - start) > 0:
            return DirtyHTML(data[start:self._i], self._in_tag)
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

original = "pl"
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
        original_lang=original,
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
        builder.lang = self.lang
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


def main():
    if len(sys.argv) < 2:
        usage()
        error("")
        raise ValueError("Error: You must specify a language to check.")
    nextLang = sys.argv[1]
    langDotExt = JGALPack.default_langDotExt
    origLangSub = original + langDotExt
    origLangPath = os.path.join(langsPath, origLangSub)
    if nextLang == original:
        langs = existingLangs([origLangSub])
        usage()
        error("")
        raise ValueError("You must specify a language to check, but"
                         " you specified the original language ({})."
                         " You must specify a language such as one "
                         " in \"{}\":"
                         " {}".format(original, langsPath, langs))
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
        raise ValueError("Error: \"{}\" is missing (original={},"
                         " langDotExt={})"
                         "".format(origLangPath, original,
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
    origPack = JGALPack(langsPath, origLangSub, original)
    for key in origPack.keys:
        nextPhrase = nextPack.phrases.get(key)
        # ^ See if the original language key is in the target language.
        if nextPhrase is not None:
            # It already is in the target.
            continue
        # nextPhrase is None, so generate it through translation.
        origPhrase = origPack.phrases[key]
        debug("translate {}".format(origPhrase.value))
        nextValue = ""
        for chunk in ParseDirtyHTML(origPhrase.value,
                                    origPack.getPath(),
                                    origPhrase.lineN,
                                    origPhrase.vCol):
            if chunk.is_html:
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
                # tmp = translate(tmp)
                if escapeQ is not None:
                    tmp = tmp.replace(escapeQ, "\\" + escapeQ)
                nextValue += tmp
        gQ = origPhrase.gQ
        lQ = origPhrase.lQ
        kQ = origPhrase.kQ

        for extra in origPhrase.extras:
            print(extra)
        nextPhrase = origPhrase.reconstruct(nextLang, nextValue)
        print(nextPhrase.toCode())


if __name__ == "__main__":
    main()
