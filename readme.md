# justgetalang
Can't we all just get a lang? Make one language php file from another using Google Translate's automatic translation via the `googletrans` PyPI package.

## License
This program is GPL v2.1 or higher.

## Use
This program will mimic and translate any files using the syntax: `{globalsName}['{translationsKey}']['key'] = 'value'` where `key` is any language key compatible with Google Translate such as 'en' or 'pl'.
- Examples:
  - `$GLOBALS['translations']['es'][key] = 'Hola'` then run the program and get:
  - `$GLOBALS['translations']['en'][key] = 'Hello'`
    - You can run when the lang/es.php has dozens of lines like that: justgetalang will print all of the lines that are missing to standard output and cache them to trCache.json in the current directory.
- The file may use any type of quotes, and the type of quote will be preserved on a per-key per-line basis.
- You can change `JGALPack.globalsName` to something other than `$GLOBLALS`.
- You can change `JGALPack.translationsKey` to something other than `translations`.

This can be used along with Poikilos' GPL v.3 translations.php from AngularCMS, but you don't need to use it, and you don't to use any version of Angular at all. You don't even need to use PHP if you change the static variables listed above.

Example:
```
mkdir -p ~/git
cd ~/git
git clone https://github.com/poikilos/justgetalang.git

#The a compatible version of the following repo should be available on or after 2021-07-28
cd /tmp
git clone https://github.com/poikilos/AngularCMS.git
cd AngularCMS
git fetch
git checkout internationalization

python3 ~/git/justgetalang/justgetalang.py en
```
