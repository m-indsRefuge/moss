import QtQuick
import QtQuick.Controls
import QtQuick.Shapes

// A decorative place for the existing creature. Only completed backend actions
// reach perform(); the slow foliage drift changes visual properties alone.
Item {
    id: habitat
    required property QtObject bridge
    readonly property real floorY: height * 0.77
    readonly property real creatureScale: Math.min(1.65, Math.max(1.2, height / 305))
    readonly property string pose: creature.state

    function perform(action) { creature.perform(action) }

    // The arch is drawn in normalized coordinates so its crown and ground
    // remain one composition at every window size.
    Shape {
        id: alcove
        x: habitat.width * 0.025; y: 6
        width: habitat.width * 0.95; height: habitat.height * 0.91
        readonly property real springY: Math.min(width * 0.47, height * 0.66)
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: "#394338"; strokeWidth: 1
            fillGradient: LinearGradient {
                x1: 0; y1: 0; x2: alcove.width * 0.65; y2: alcove.height
                GradientStop { position: 0; color: "#293b2d" }
                GradientStop { position: 0.55; color: "#182b22" }
                GradientStop { position: 1; color: "#13221b" }
            }
            startX: 0; startY: alcove.height
            PathLine { x: 0; y: alcove.springY }
            PathCubic { x: alcove.width; y: alcove.springY; control1X: 0; control1Y: -alcove.springY / 3; control2X: alcove.width; control2Y: -alcove.springY / 3 }
            PathLine { x: alcove.width; y: alcove.height }
            PathLine { x: 0; y: alcove.height }
        }
    }
    // A second fine arch and a quiet beam establish depth without busy texture.
    Shape {
        x: alcove.x + 11; y: alcove.y + 11
        width: alcove.width - 22; height: alcove.height - 22
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: "#364333"; strokeWidth: 1; fillColor: "transparent"
            startX: 0; startY: habitat.floorY * 0.89
            PathLine { x: 0; y: alcove.springY - 8 }
            PathCubic { x: alcove.width - 22; y: alcove.springY - 8; control1X: 0; control1Y: -alcove.springY / 3; control2X: alcove.width - 22; control2Y: -alcove.springY / 3 }
            PathLine { x: alcove.width - 22; y: habitat.floorY * 0.89 }
        }
    }
    Shape {
        width: parent.width; height: parent.height
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: 0
            fillGradient: LinearGradient {
                x1: habitat.width * 0.25; y1: 35; x2: habitat.width * 0.65; y2: habitat.floorY
                GradientStop { position: 0; color: "#0eaaa77a" }
                GradientStop { position: 1; color: "#00aaa77a" }
            }
            startX: habitat.width * 0.24; startY: habitat.height * 0.13
            PathLine { x: habitat.width * 0.47; y: habitat.height * 0.1 }
            PathLine { x: habitat.width * 0.82; y: habitat.floorY }
            PathLine { x: habitat.width * 0.42; y: habitat.floorY }
            PathLine { x: habitat.width * 0.24; y: habitat.height * 0.13 }
        }
    }

    // Two broad botanical silhouettes, behind the creature rather than around
    // every edge. Leaves are fixed artwork, not a new environmental system.
    component Frond: Item {
        id: frond
        property color ink: "#304b37"
        property real drift: 0
        transformOrigin: Item.Bottom
        rotation: drift
        SequentialAnimation on drift {
            running: frond.visible; loops: Animation.Infinite
            NumberAnimation { to: 1.2; duration: 6500; easing.type: Easing.InOutSine }
            NumberAnimation { to: -1.2; duration: 7500; easing.type: Easing.InOutSine }
        }
        Shape {
            anchors.fill: parent; preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: frond.ink; strokeWidth: 2; fillColor: "transparent"
                startX: frond.width * 0.48; startY: frond.height
                PathCubic { x: frond.width * 0.34; y: 0; control1X: frond.width * 0.7; control1Y: frond.height * 0.58; control2X: frond.width * 0.06; control2Y: frond.height * 0.2 }
            }
        }
        Repeater {
            model: 6
            Shape {
                id: leaf
                required property int index
                readonly property bool facesLeft: index % 2 === 0
                x: frond.width * (facesLeft ? 0.1 : 0.37)
                y: frond.height * (0.12 + index * 0.115)
                width: frond.width * 0.52; height: frond.height * 0.2
                rotation: facesLeft ? -24 : 12
                preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    strokeWidth: 0; fillColor: frond.ink
                    startX: leaf.facesLeft ? leaf.width : 0; startY: leaf.height
                    PathCubic { x: leaf.facesLeft ? 0 : leaf.width; y: 0; control1X: leaf.width * 0.15; control1Y: leaf.height * 0.75; control2X: leaf.width * 0.2; control2Y: leaf.height * 0.2 }
                    PathCubic { x: leaf.facesLeft ? leaf.width : 0; y: leaf.height; control1X: leaf.width * 0.75; control1Y: leaf.height * 0.1; control2X: leaf.width * 0.9; control2Y: leaf.height * 0.5 }
                }
            }
        }
    }
    Frond {
        x: habitat.width * 0.04; y: habitat.floorY - height
        width: habitat.width * 0.26; height: habitat.height * 0.45
        ink: "#2c4232"; opacity: 0.7
    }
    Frond {
        x: habitat.width * 0.72; y: habitat.floorY - height + 5
        width: habitat.width * 0.21; height: habitat.height * 0.59
        ink: "#2c4331"; opacity: 0.65
        transform: Scale { xScale: -1; origin.x: habitat.width * 0.105 }
    }

    // A deep, low stone shelf gives Moss actual ground and the bowl a place.
    Shape {
        id: ground
        x: 0; y: habitat.floorY - 10
        width: habitat.width; height: habitat.height - y
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: 0; fillColor: "#0c1712"
            startX: ground.width * 0.02; startY: 26
            PathCubic { x: ground.width * 0.96; y: 29; control1X: ground.width * 0.32; control1Y: 3; control2X: ground.width * 0.77; control2Y: 1 }
            PathLine { x: ground.width * 0.92; y: ground.height * 0.8 }
            PathCubic { x: ground.width * 0.1; y: ground.height * 0.86; control1X: ground.width * 0.68; control1Y: ground.height * 1.02; control2X: ground.width * 0.28; control2Y: ground.height * 1.01 }
            PathLine { x: ground.width * 0.02; y: 26 }
        }
        ShapePath {
            strokeWidth: 0
            fillGradient: LinearGradient {
                x1: 0; y1: 12; x2: 0; y2: ground.height * 0.83
                GradientStop { position: 0; color: "#344635" }
                GradientStop { position: 1; color: "#1d2c23" }
            }
            startX: ground.width * 0.03; startY: 14
            PathCubic { x: ground.width * 0.97; y: 17; control1X: ground.width * 0.2; control1Y: -5; control2X: ground.width * 0.81; control2Y: -10 }
            PathLine { x: ground.width * 0.93; y: ground.height * 0.67 }
            PathCubic { x: ground.width * 0.07; y: ground.height * 0.72; control1X: ground.width * 0.71; control1Y: ground.height * 0.88; control2X: ground.width * 0.28; control2Y: ground.height * 0.92 }
            PathLine { x: ground.width * 0.03; y: 14 }
        }
        ShapePath {
            strokeColor: "#536142"; strokeWidth: 1; fillColor: "#41543b"
            startX: ground.width * 0.03; startY: 14
            PathCubic { x: ground.width * 0.97; y: 17; control1X: ground.width * 0.2; control1Y: -5; control2X: ground.width * 0.81; control2Y: -10 }
            PathCubic { x: ground.width * 0.03; y: 14; control1X: ground.width * 0.88; control1Y: 44; control2X: ground.width * 0.18; control2Y: 39 }
        }
        ShapePath {
            strokeColor: "#344536"; strokeWidth: 1; fillColor: "transparent"
            startX: ground.width * 0.14; startY: ground.height * 0.56
            PathCubic { x: ground.width * 0.8; y: ground.height * 0.51; control1X: ground.width * 0.34; control1Y: ground.height * 0.69; control2X: ground.width * 0.57; control2Y: ground.height * 0.43 }
        }
    }
    Creature {
        id: creature; objectName: "creature"
        x: habitat.width * 0.45 - width / 2
        y: habitat.floorY - height + 13
        scale: habitat.creatureScale; transformOrigin: Item.Bottom
        visible: bridge.ready; mood: bridge.mood
    }
    Label {
        anchors.centerIn: parent; textFormat: Text.PlainText
        visible: !bridge.ready; color: "#9fa892"; font.pixelSize: 13
        text: bridge.busy ? "Opening home…" : "Moss could not be loaded"
    }
    FoodBowl {
        id: foodBowl; objectName: "foodBowl"
        x: habitat.width * 0.73
        y: habitat.floorY - height * 0.52
        width: Math.max(82, Math.min(104, habitat.width * 0.19))
        height: width * 0.74
        visible: bridge.ready
        commitCount: bridge.ready ? bridge.bowl : 0
        eating: habitat.pose === "eat"
    }
    Frond {
        x: habitat.width * 0.09; y: habitat.floorY - height + 43
        width: habitat.width * 0.13; height: habitat.height * 0.2; ink: "#465b3e"
    }
}
