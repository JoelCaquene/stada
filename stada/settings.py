"""
Django settings for stada project.
Configurado para Testagem Local e Produção no Render.com.
"""

from pathlib import Path
import os
import dj_database_url
from decouple import config
from django.utils.translation import gettext_lazy as _

# Caminho base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# SEGURANÇA: DEBUG deve ser False em produção
DEBUG = config('DEBUG', default=False, cast=bool)

SECRET_KEY = config('SECRET_KEY', default='django-insecure-mudar-isso-em-producao')

# ======================================================================
# CONFIGURAÇÃO DOS HOSTS PERMITIDOS E CSRF
# ======================================================================

raw_hosts = config('ALLOWED_HOSTS', default='127.0.0.1,localhost').split(',')
ALLOWED_HOSTS = [host.strip() for host in raw_hosts if host.strip()]

render_hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)

# Teu link no Render (stada.onrender.com) e domínios do projeto
for domain in ['stada.onrender.com', 'stada.pro', 'www.stada.pro']:
    if domain not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(domain)

# Deixa False enquanto usas stada.onrender.com para evitar redirecionamento para www.stada.onrender.com
PREPEND_WWW = config('PREPEND_WWW', default=False, cast=bool)

# Origens confiáveis para CSRF (inclui https://stada.onrender.com)
CSRF_TRUSTED_ORIGINS = [
    f"https://{host}"
    for host in ALLOWED_HOSTS
    if host not in ('127.0.0.1', 'localhost', '*')
]

# ======================================================================
# APPS E MIDDLEWARE
# ======================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'stada.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'stada.wsgi.application'

# ======================================================================
# DATABASE (SQLITE LOCAL / POSTGRES EM PRODUÇÃO)
# ======================================================================

DATABASE_URL = config('DATABASE_URL', default='')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=not DEBUG,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ======================================================================
# INTERNACIONALIZAÇÃO
# ======================================================================

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'Africa/Luanda'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('pt', _('Português')),
    ('en', _('English')),
    ('fr', _('Français')),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# ======================================================================
# STATIC, STORAGES E MEDIA FILES
# ======================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

static_dir = BASE_DIR / 'static'
STATICFILES_DIRS = [static_dir] if static_dir.exists() else []

if not DEBUG:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ======================================================================
# SEGURANÇA EXTRA (ATIVADA APENAS EM PRODUÇÃO)
# ======================================================================

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'core.CustomUser'
LOGIN_URL = 'login'
