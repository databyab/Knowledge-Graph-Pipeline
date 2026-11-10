from ekg.api.security import IpRateLimiter
from ekg.extract.prompts import make_user


def test_ip_rate_limiter() -> None:
    limiter = IpRateLimiter(limit=1)
    assert limiter.allow("127.0.0.1")
    assert not limiter.allow("127.0.0.1")


def test_source_prompt_does_not_include_gold_chunk_ids() -> None:
    prompt = make_user("gold_v1:0 source text")
    assert "gold_v1:0" not in prompt
