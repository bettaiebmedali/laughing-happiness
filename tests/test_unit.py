from app.main import sum_values, SumRequest


def test_sum_values():
    assert sum_values(SumRequest(a=2, b=3)) == {"result": 5}


def test_sum_supports_negative_numbers():
    assert sum_values(SumRequest(a=-2, b=1)) == {"result": -1}
