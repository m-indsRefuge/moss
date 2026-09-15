from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "src" / "moss" / "qml" / "Home.qml"


def test_vitals_have_illustrated_botanical_meters_and_stay_presentation_only():
    source = HOME.read_text(encoding="utf-8")

    meter_start = source.index("component Meter: ColumnLayout")
    meter_end = source.index("// One still wash")
    meter = source[meter_start:meter_end]

    for marker in (
        "required property color accent",
        "required property color accentDeep",
        'objectName: "meterRail"',
        'objectName: "meterFill"',
        'objectName: "meterHighlight"',
    ):
        assert marker in meter

    vitals_start = source.index('objectName: "vitals"')
    vitals_end = source.index('id: notes; objectName: "notesRegion"')
    vitals = source[vitals_start:vitals_end]

    for marker in (
        'objectName: "hungerMeter"',
        'caption: "Hunger"',
        "level: bridge.hunger",
        'objectName: "energyMeter"',
        'caption: "Energy"',
        "level: bridge.energy",
    ):
        assert marker in vitals

    forbidden = (
        "requestTick(",
        "requestClose(",
        "open()",
        "moss.state.json",
        "subprocess",
        "ollama",
        "qwen",
    )
    lowered = (meter + vitals).lower()
    assert all(token.lower() not in lowered for token in forbidden)
