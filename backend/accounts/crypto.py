import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings

_f = Fernet(base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest()))
encrypt = lambda s: _f.encrypt(s.encode()).decode()
decrypt = lambda s: _f.decrypt(s.encode()).decode()
