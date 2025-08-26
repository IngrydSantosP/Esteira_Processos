import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

# Cache de configuração
@lru_cache(maxsize=1)
def get_config():
    return {
        'MODO_IA': os.getenv('MODO_IA', 'local'),
        'TOP_JOBS': int(os.getenv('TOP_JOBS', '3'))
    }


