"""
python -m scripts.seed demo
python -m scripts.seed loadtest --n 100000 --out loadtest/tokens.json
python -m scripts.seed cleanup-loadtest
"""
import argparse, json, math, random

from app.cache import feed_drop
from app.db import pool
from app.embeddings import embed
from app.security import hash_pw, make_token

DEMO = [
    ("anna@orbita.dev", "orbita-anna-2026", "Анна", 27, "user",
     ["бег", "кофе", "джаз", "фотография", "путешествия"], "Бегаю по утрам, по вечерам — плёночная камера и джаз."),
    ("max@orbita.dev", "orbita-max-2026", "Максим", 29, "user",
     ["марафоны", "эспрессо", "винил", "походы", "фотоаппараты"], "Готовлюсь к третьему марафону. Собираю пластинки."),
    ("admin@orbita.dev", "orbita-admin-2026", "Модератор", 30, "admin",
     ["модерация", "безопасность", "чтение", "кино", "шахматы"], "Служебный аккаунт модерации."),
    ("kate@orbita.dev", "orbita-demo-2026", "Катя", 25, "user",
     ["йога", "чай", "керамика", "ботаника", "акварель"], "Леплю чашки и выращиваю монстеры."),
    ("ilya@orbita.dev", "orbita-demo-2026", "Илья", 31, "user",
     ["настолки", "программирование", "научная фантастика", "велосипед", "кофе"], "Собираю компанию на «Каркассон»."),
    ("sofia@orbita.dev", "orbita-demo-2026", "София", 26, "user",
     ["танцы", "джаз", "театр", "путешествия", "французский язык"], "Свинг по средам, театр по выходным."),
    ("dmitry@orbita.dev", "orbita-demo-2026", "Дмитрий", 34, "user",
     ["скалолазание", "горы", "походы", "фотография", "трейлраннинг"], "Лето в горах, зима на скалодроме."),
]


def upsert(c, email, pw, name, age, role, tags, bio):
    return c.execute(
        "INSERT INTO users(email, pw_hash, name, age, role, tags, emb, bio, email_verified_at) "
        "VALUES(%s,%s,%s,%s,%s,%s,%s::vector,%s,now()) ON CONFLICT (email) DO UPDATE SET "
        "pw_hash=EXCLUDED.pw_hash, name=EXCLUDED.name, age=EXCLUDED.age, role=EXCLUDED.role, tags=EXCLUDED.tags, "
        "emb=EXCLUDED.emb, bio=EXCLUDED.bio, email_verified_at=COALESCE(users.email_verified_at, now()), "
        "banned_at=NULL, hidden_at=NULL RETURNING id",
        (email, hash_pw(pw), name, age, role, sorted(tags), str(embed(tags)), bio)).fetchone()["id"]


def demo():
    with pool.connection() as c:
        ids = {d[0]: upsert(c, *d) for d in DEMO}
        anna, mx = ids["anna@orbita.dev"], ids["max@orbita.dev"]
        c.execute("INSERT INTO swipes(swiper,target,liked) VALUES(%s,%s,true),(%s,%s,true) "
                  "ON CONFLICT (swiper,target) DO UPDATE SET liked=true", (anna, mx, mx, anna))
        a, b = sorted((anna, mx))
        c.execute("INSERT INTO matches(a,b) VALUES(%s,%s) ON CONFLICT DO NOTHING", (a, b))
        if not c.execute("SELECT 1 FROM messages WHERE a=%s AND b=%s", (a, b)).fetchone():
            c.execute("INSERT INTO messages(a,b,sender,body) VALUES(%s,%s,%s,%s),(%s,%s,%s,%s)",
                      (a, b, mx, "Привет! Вижу, ты тоже бегаешь. Какая дистанция любимая?",
                       a, b, anna, "Привет! Десятка, но давно думаю про полумарафон 🙂"))
    feed_drop(*ids.values())
    print("Демо-аккаунты:")
    for email, pw, name, _, role, *_ in DEMO:
        print(f"  {email:22} {pw:20} {name}{' (admin)' if role == 'admin' else ''}")


VOCAB = ("бег марафоны йога кофе чай джаз рок винил театр кино сериалы аниме настолки шахматы "
         "программирование дизайн фотография живопись акварель керамика книги поэзия философия история "
         "путешествия походы горы велосипед плавание сёрфинг сноуборд скалолазание танцы вокал гитара "
         "кулинария выпечка вино крафтовое пиво собаки кошки садоводство астрономия наука стартапы "
         "волонтёрство языки психология медитация футбол теннис баскетбол бокс").split()


def loadtest(n, out, swipes):
    rnd = random.Random(42)
    vecs = {t: embed([t]) for t in VOCAB}
    pw = hash_pw("loadtest-password")
    with pool.connection() as c, c.cursor() as cur:
        cur.execute("SET LOCAL maintenance_work_mem = '512MB'")
        cur.execute("SET LOCAL max_parallel_maintenance_workers = 4")
        cur.execute("DELETE FROM users WHERE email LIKE 'lt%%@orbita.test'")
        cur.execute("DROP INDEX IF EXISTS users_emb_hnsw")
        with cur.copy("COPY users(email, pw_hash, name, age, tags, emb, email_verified_at) FROM STDIN") as cp:
            for i in range(n):
                tags = rnd.sample(VOCAB, rnd.randint(5, 8))
                m = [sum(col) / len(tags) for col in zip(*(vecs[t] for t in tags))]
                norm = math.sqrt(sum(x * x for x in m)) or 1.0
                cp.write_row((f"lt{i}@orbita.test", pw, f"Нагрузка {i}", rnd.randint(18, 60), sorted(tags),
                              str([x / norm for x in m]), "2026-01-01T00:00:00Z"))
        ids = [r["id"] for r in c.execute(
            "SELECT id FROM users WHERE email LIKE 'lt%%@orbita.test' ORDER BY id").fetchall()]
        print(f"users: {len(ids)}, building hnsw index...")
        cur.execute("CREATE INDEX users_emb_hnsw ON users USING hnsw (emb vector_cosine_ops)")
        if swipes:
            with cur.copy("COPY swipes(swiper, target, liked) FROM STDIN") as cp:
                for uid in ids:
                    for t in set(rnd.sample(ids, swipes)) - {uid}:
                        cp.write_row((uid, t, rnd.random() < 0.3))
            print(f"swipes: ~{len(ids) * swipes}")
    with open(out, "w") as f:
        json.dump([make_token(i, ttl=7 * 86400) for i in ids], f)
    print(f"tokens: {out}")


def cleanup_loadtest():
    with pool.connection() as c:
        n = c.execute("DELETE FROM users WHERE email LIKE 'lt%%@orbita.test'").rowcount
    print(f"deleted {n} loadtest users")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["demo", "loadtest", "cleanup-loadtest"])
    ap.add_argument("--n", type=int, default=100000)
    ap.add_argument("--out", default="loadtest/tokens.json")
    ap.add_argument("--swipes", type=int, default=50)
    args = ap.parse_args()
    pool.open(wait=True)
    try:
        {"demo": demo, "loadtest": lambda: loadtest(args.n, args.out, args.swipes),
         "cleanup-loadtest": cleanup_loadtest}[args.cmd]()
    finally:
        pool.close()
