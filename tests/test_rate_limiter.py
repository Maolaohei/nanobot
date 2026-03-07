from nanobot.utils.rate_limiter import TokenBucket

def test_token_bucket_burst_then_wait_window():
    tb = TokenBucket(rate_per_sec=2.0, capacity=2)
    assert tb.consume(1) == 0.0
    assert tb.consume(1) == 0.0
    wait = tb.consume(1)
    assert 0.3 <= wait <= 0.8
