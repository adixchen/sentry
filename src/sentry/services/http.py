"""
sentry.services.http
~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010-2016 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""
from __future__ import absolute_import, print_function

import os
import sys
from sentry.services.base import Service


def add_option_to_env(k, v):
    key = 'UWSGI_' + k.upper().replace('-', '_')
    if isinstance(v, basestring):
        value = v
    elif v is True:
        value = 'true'
    elif v is False:
        value = 'false'
    elif isinstance(v, (int, long)):
        value = str(v)
    else:
        raise TypeError('Unknown option type: %r (%s)' % (k, type(v)))
    os.environ[key] = value


class SentryHTTPServer(Service):
    name = 'http'

    def __init__(self, host=None, port=None, debug=False, workers=None,
                 validate=True):
        from django.conf import settings

        if validate:
            self.validate_settings()

        self.host = host or settings.SENTRY_WEB_HOST
        self.port = port or settings.SENTRY_WEB_PORT
        self.workers = workers

        options = (settings.SENTRY_WEB_OPTIONS or {}).copy()
        options.setdefault('module', 'sentry.wsgi:application')
        options.setdefault('protocol', 'http')
        options.setdefault('http-socket', '%s:%s' % (self.host, self.port))
        options.setdefault('auto-procname', True)
        options.setdefault('procname-prefix-spaced', '[Sentry]')
        options.setdefault('workers', 3)
        options.setdefault('threads', 1)
        options.setdefault('http-timeout', 30)
        options.setdefault('vacuum', True)
        options.setdefault('thunder-lock', True)
        options.setdefault('log-x-forwarded-for', False)
        options.setdefault('buffer-size', 32768)
        options.setdefault('post-buffering', 65536)
        options.setdefault('limit-post', 20971520)
        options.setdefault('need-app', True)
        options.setdefault('disable-logging', False)
        options.setdefault('memory-report', True)
        options.setdefault('reload-on-rss', 600)
        options.setdefault('ignore-sigpipe', True)
        options.setdefault('ignore-write-errors', True)
        options.setdefault('disable-write-exception', True)
        options.setdefault('virtualenv', sys.prefix)
        options.setdefault('log-format', '%(addr) - %(user) [%(ltime)] "%(method) %(uri) %(proto)" %(status) %(size) "%(referer)" "%(uagent)"')
        options.setdefault('uid', os.getuid())
        options.setdefault('gid', os.getgid())

        # Required arguments that should not be overridden
        options['master'] = True
        options['enable-threads'] = True
        options['lazy-apps'] = True
        options['single-interpreter'] = True

        if workers:
            options['workers'] = workers

        # Old options from gunicorn
        if 'bind' in options:
            options['http-socket'] = options['bind']
            del options['bind']
        if 'accesslog' in options:
            if options['accesslog'] != '-':
                options['logto'] = options['accesslog']
            del options['accesslog']
        if 'errorlog' in options:
            if options['errorlog'] != '-':
                options['logto2'] = options['errorlog']
            del options['errorlog']
        if 'timeout' in options:
            options['http-timeout'] = options['timeout']
            del options['timeout']
        if 'proc_name' in options:
            options['procname-prefix-spaced'] = options['proc_name']
            del options['proc_name']
        if 'secure_scheme_headers' in options:
            del options['secure_scheme_headers']
        if 'loglevel' in options:
            del options['loglevel']

        self.options = options

    def validate_settings(self):
        from django.conf import settings as django_settings
        from sentry.utils.settings import validate_settings

        validate_settings(django_settings)

    def run(self):
        for k, v in self.options.iteritems():
            if v is not None:
                add_option_to_env(k, v)

        # This has already been validated inside __init__
        os.environ['SENTRY_SKIP_BACKEND_VALIDATION'] = '1'

        os.execvp('uwsgi', ('uwsgi',))
