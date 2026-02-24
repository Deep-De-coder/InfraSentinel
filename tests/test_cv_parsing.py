from packages.cv.parsing import parse_cable_tag, parse_port_label


def test_parse_port_label_port_keyword() -> None:
    value, conf = parse_port_label("PORT 24")
    assert value == "24"
    assert conf > 0.8


def test_parse_port_label_p_short() -> None:
    value, _ = parse_port_label("P24")
    assert value == "24"


def test_parse_port_label_alpha() -> None:
    value, _ = parse_port_label("A12")
    assert value == "A12"


def test_parse_cable_tag_pattern() -> None:
    value, conf = parse_cable_tag("MDF-01-R12-P24")
    assert value == "MDF-01-R12-P24"
    assert conf >= 0.9
