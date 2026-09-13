from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HABITAT = ROOT / "src" / "moss" / "qml" / "Habitat.qml"
FOOD_BOWL = ROOT / "src" / "moss" / "qml" / "FoodBowl.qml"


def test_food_bowl_is_a_presentational_component_bound_to_bridge_projection():
    """Protect the FOOD-01 component boundary without pixel assertions."""
    assert FOOD_BOWL.exists(), "FOOD-01 requires a dedicated FoodBowl.qml component"

    habitat = HABITAT.read_text(encoding="utf-8")
    bowl = FOOD_BOWL.read_text(encoding="utf-8")

    assert "FoodBowl {" in habitat
    assert 'objectName: "foodBowl"' in habitat
    assert "commitCount: bridge.ready ? bridge.bowl : 0" in habitat
    assert 'eating: habitat.pose === "eat"' in habitat

    assert "property int commitCount" in bowl
    assert "property bool eating" in bowl
    assert "readonly property int tokenCount" in bowl
    assert "Math.min(Math.max(commitCount, 0), 7)" in bowl
    assert 'objectName: "bowlLabel"' in bowl

    # The component may render projected state, but it must never own authority.
    forbidden = (
        "requestTick(",
        "requestClose(",
        "live_tick",
        "moss.state.json",
        "subprocess",
        "git ",
        "ollama",
        "qwen",
    )
    lowered = bowl.lower()
    assert not any(term.lower() in lowered for term in forbidden)
