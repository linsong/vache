import sqlite3
import plistlib
import platform
import os
import sys
import cPickle

USER_CACHE_DIR = None
if platform.system() == 'Windows':
    USER_CACHE_DIR = os.environ['LocalAppData']
elif platform.system() == 'Linux':
    try:
        USER_CACHE_DIR = os.environ['XDG_CACHE_HOME']
    except KeyError:
        USER_CACHE_DIR = os.path.join(os.environ['HOME'], '.cache')
elif platform.system() == 'Darwin':
    USER_CACHE_DIR = os.path.join(os.environ['HOME'], 'Library/Caches')
else:
    print 'could not recognise platform: ', platform.system()
    sys.exit(1)

CACHE_DIR = os.path.join(USER_CACHE_DIR, 'vache')
PLIST_CACHE = os.path.join(
    CACHE_DIR, 'plist.cache.sqlite3'
)
LOG_DB = os.path.join(CACHE_DIR, 'log.sqlite3')
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

if not os.path.exists(PLIST_CACHE):
    conn = sqlite3.connect(PLIST_CACHE)
    conn.execute('CREATE TABLE t (path BLOB, plist BLOB)')

if not os.path.exists(LOG_DB):
    conn = sqlite3.connect(LOG_DB)
    conn.execute('CREATE TABLE t (doc_db TEXT, error TEXT)')


def get_names(doc_db):
    conn = sqlite3.connect(doc_db)
    return conn.execute('SELECT name FROM searchIndex')


def get_uri_path(doc_db, name):
    conn = sqlite3.connect(doc_db)
    (uri,) = conn.execute(
        'SELECT path FROM searchIndex WHERE name = ?', (name,)
    ).fetchone()
    return uri


def log_bad_docset_db(doc_db, error):
    with sqlite3.connect(LOG_DB) as conn:
        conn.execute(
            'INSERT INTO t (doc_db, error) VALUES (?, ?)',
            (doc_db, unicode(error))
        )


def retrying(f, x):
    try:
        return f(x)
    except:
        return retrying(f, x)


def fetchplists(paths):
    with sqlite3.connect(PLIST_CACHE) as conn:
        conn.text_factory = str
        c = conn.cursor()

        cache = {}
        c.execute('SELECT * FROM t')
        for path, plist in c:
            cache[path] = cPickle.loads(plist)

        newInserts = {}

        for path in paths:
            if not path:
                break

            if path in cache:
                yield cache[path], path
            else:
                parsed = plistlib.readPlist(path)
                cache[path] = parsed
                newInserts[path] = cPickle.dumps(parsed)
                yield parsed, path

        c.executemany(
            'INSERT INTO t (path, plist) VALUES (?, ?)',
            newInserts.iteritems()
        )
