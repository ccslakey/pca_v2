from pca_backend.observability import scrub_event, scrub_query_string


def test_query_string_keeps_only_allowlisted_params():
    qs = 'compare=ruthba01,bondsba01&email=a@b.com&fbclid=xyz&utm_source=reddit'
    assert scrub_query_string(qs) == 'compare=ruthba01%2Cbondsba01&utm_source=reddit'


def test_scrub_event_strips_request_metadata_and_user():
    event = {
        'request': {
            'url': 'https://example.com/api/players/',
            'method': 'GET',
            'headers': {'X-Forwarded-For': '1.2.3.4', 'User-Agent': 'x'},
            'cookies': {'sessionid': 'abc'},
            'data': {'q': 'free text'},
            'env': {'REMOTE_ADDR': '1.2.3.4'},
            'query_string': 'compare=ruthba01&gclid=zzz',
        },
        'user': {'ip_address': '1.2.3.4'},
    }
    out = scrub_event(event)
    assert out['request'] == {
        'url': 'https://example.com/api/players/',
        'method': 'GET',
        'query_string': 'compare=ruthba01',
    }
    assert 'user' not in out


def test_scrub_event_drops_non_string_query_string():
    out = scrub_event({'request': {'query_string': [('email', 'a@b.com')]}})
    assert 'query_string' not in out['request']
