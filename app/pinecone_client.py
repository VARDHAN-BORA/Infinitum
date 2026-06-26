from pinecone import Pinecone
from app.config import settings

EMBED_TEXT_FIELD = "text"
PINECONE_NAMESPACE = ""

_pc = Pinecone(api_key=settings.PINECONE_API_KEY.strip())

_index = None


def get_index():
    global _index
    if _index is None:
        _host = _pc.describe_index(settings.PINECONE_INDEX_NAME.strip()).host
        _index = _pc.Index(host=_host)
    return _index
