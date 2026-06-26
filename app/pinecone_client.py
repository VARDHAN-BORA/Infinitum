from pinecone import Pinecone
from app.config import settings

# The field name that Pinecone uses to embed text — must match the field_map
# set in your index embed configuration (Pinecone console default: "text").
EMBED_TEXT_FIELD = "text"

# Empty string is Pinecone's built-in default namespace.
PINECONE_NAMESPACE = ""

# Resolve the index host once at process startup, then hold a single
# shared client and index handle for every module that needs Pinecone.
# Both ingestion.py and query.py import from here — no duplicate clients,
# no duplicate describe_index() network calls.
_pc = Pinecone(api_key=settings.PINECONE_API_KEY.strip())
_host = _pc.describe_index(settings.PINECONE_INDEX_NAME.strip()).host
index = _pc.Index(host=_host)
