import hashlib, json, logging, math, urllib.request

import redis

from . import config

log = logging.getLogger(__name__)
DIM = 384
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
TAG_TTL = 30 * 86400
_model = None


def load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def hash_vec(text):
    v = [0.0] * DIM
    for tok in text.lower().split():
        v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM] += 1.0
    return v


def _compute(tags):
    if config.EMBEDDINGS == "hash":
        return [hash_vec(t) for t in tags]
    if config.EMBEDDINGS == "remote":
        req = urllib.request.Request(config.EMBEDDER_URL + "/embed", json.dumps({"tags": tags}).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)["vectors"]
    try:
        return load_model().encode(tags).tolist()
    except Exception:
        log.warning("model unavailable, using hash embeddings")
        return [hash_vec(t) for t in tags]


def encode(tags):
    from .cache import r
    keys = [f"emb:{config.EMBEDDINGS}:{t}" for t in tags]
    try:
        cached = r.mget(keys)
    except redis.RedisError:
        cached = [None] * len(tags)
    out = [json.loads(c) if c else None for c in cached]
    missing = [i for i, v in enumerate(out) if v is None]
    if missing:
        fresh = _compute([tags[i] for i in missing])
        try:
            p = r.pipeline()
            for i, v in zip(missing, fresh):
                out[i] = v
                p.set(keys[i], json.dumps([round(x, 6) for x in v]), ex=TAG_TTL)
            p.execute()
        except redis.RedisError:
            for i, v in zip(missing, fresh):
                out[i] = v
    return out


def embed(tags):
    # user vector = normalized mean of tag vectors
    vs = encode(tags)
    m = [sum(c) / len(vs) for c in zip(*vs)]
    n = math.sqrt(sum(x * x for x in m)) or 1.0
    return [x / n for x in m]
