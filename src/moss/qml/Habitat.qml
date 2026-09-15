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
            strokeColor: "#29392e"; strokeWidth: 1
            fillGradient: LinearGradient {
                x1: 0; y1: 0; x2: alcove.width * 0.65; y2: alcove.height
                GradientStop { position: 0; color: "#2c3e2e" }
                GradientStop { position: 0.55; color: "#1a2d23" }
                GradientStop { position: 1; color: "#13221b" }
            }
            startX: 0; startY: alcove.height
            PathLine { x: 0; y: alcove.springY }
            PathCubic { x: alcove.width; y: alcove.springY; control1X: 0; control1Y: -alcove.springY / 3; control2X: alcove.width; control2Y: -alcove.springY / 3 }
            PathLine { x: alcove.width; y: alcove.height }
            PathLine { x: 0; y: alcove.height }
        }
    }
    // The inner seal sits behind selective reflections on the outer glass.
    Shape {
        x: alcove.x + 11; y: alcove.y + 11
        width: alcove.width - 22; height: alcove.height - 22
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: "#2d3e30"; strokeWidth: 1; fillColor: "transparent"
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
                GradientStop { position: 0; color: "#05aaa77a" }
                GradientStop { position: 1; color: "#00aaa77a" }
            }
            startX: habitat.width * 0.24; startY: habitat.height * 0.13
            PathQuad { x: habitat.width * 0.47; y: habitat.height * 0.1; controlX: habitat.width * 0.34; controlY: habitat.height * 0.08 }
            PathQuad { x: habitat.width * 0.72; y: habitat.floorY; controlX: habitat.width * 0.52; controlY: habitat.height * 0.42 }
            PathLine { x: habitat.width * 0.42; y: habitat.floorY }
            PathQuad { x: habitat.width * 0.24; y: habitat.height * 0.13; controlX: habitat.width * 0.29; controlY: habitat.height * 0.42 }
        }
    }

    // A small diffuse pool shares the upper-left light with Moss. No pulse,
    // blur, offscreen layer or animated lighting is needed.
    Shape {
        anchors.fill: parent; preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: 0
            fillGradient: RadialGradient {
                centerX: habitat.width * 0.43; centerY: habitat.floorY * 0.52
                focalX: centerX; focalY: centerY
                centerRadius: habitat.height * 0.45
                GradientStop { position: 0; color: "#187e9661" }
                GradientStop { position: 1; color: "#007e9661" }
            }
            PathAngleArc { centerX: habitat.width * 0.43; centerY: habitat.floorY * 0.52; radiusX: habitat.width * 0.34; radiusY: habitat.height * 0.43; startAngle: 0; sweepAngle: 360 }
        }
    }
    Shape {
        x: alcove.x; y: alcove.y
        width: alcove.width; height: alcove.height
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: 0
            fillGradient: LinearGradient {
                x1: 0; y1: 0; x2: alcove.width * 0.18; y2: 0
                GradientStop { position: 0; color: "#14303e31" }
                GradientStop { position: 1; color: "#00303e31" }
            }
            startX: 2; startY: habitat.floorY - 12
            PathLine { x: 2; y: alcove.springY }
            PathQuad { x: alcove.width * 0.15; y: alcove.springY * 0.35; controlX: 2; controlY: alcove.springY * 0.57 }
            PathQuad { x: alcove.width * 0.09; y: alcove.springY * 1.06; controlX: alcove.width * 0.11; controlY: alcove.springY * 0.63 }
            PathLine { x: alcove.width * 0.07; y: habitat.floorY - 12 }
            PathLine { x: 2; y: habitat.floorY - 12 }
        }
        ShapePath {
            strokeColor: "#38788865"; strokeWidth: 2; fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            startX: 5; startY: alcove.springY + 5
            PathCubic { x: alcove.width * 0.338; y: alcove.springY * 0.0484 + 5; control1X: 5; control1Y: alcove.springY * 0.48 + 5; control2X: alcove.width * 0.1521 + 3; control2Y: alcove.springY * 0.1628 + 5 }
        }
        ShapePath {
            strokeColor: "#1c92a17d"; strokeWidth: 0.8; fillColor: "transparent"
            startX: alcove.width * 0.985; startY: alcove.springY + 12
            PathQuad { x: alcove.width * 0.983; y: habitat.floorY - 29; controlX: alcove.width * 0.989; controlY: (alcove.springY + habitat.floorY - 17) / 2 }
        }
    }

    // Three fixed botanical studies share a connected stem, but alternate
    // leaf length, fold and tone. Only the whole frond moves; veins are static.
    component Frond: Item {
        id: frond
        property color ink: "#304b37"
        property real drift: 0
        property int cadence: 6500
        property real rhythm: 0
        transformOrigin: Item.Bottom
        rotation: drift
        function stemX(t) {
            return width * (0.34 * Math.pow(1-t, 3) + 0.18 * Math.pow(1-t, 2)*t
                            + 2.1 * (1-t)*t*t + 0.48*t*t*t)
        }
        function stemY(t) {
            return height * (0.6 * Math.pow(1-t, 2)*t + 1.74*(1-t)*t*t + t*t*t)
        }
        SequentialAnimation on drift {
            running: frond.visible; loops: Animation.Infinite
            NumberAnimation { to: 0.7; duration: frond.cadence; easing.type: Easing.InOutSine }
            NumberAnimation { to: -0.7; duration: frond.cadence + 1600; easing.type: Easing.InOutSine }
        }
        Shape {
            anchors.fill: parent; preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: Qt.lighter(frond.ink, 1.23); strokeWidth: 1.4; fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                startX: frond.width * 0.48; startY: frond.height
                PathCubic { x: frond.width * 0.34; y: 0; control1X: frond.width * 0.7; control1Y: frond.height * 0.58; control2X: frond.width * 0.06; control2Y: frond.height * 0.2 }
            }
        }
        Repeater {
            model: 7
            Shape {
                id: leaf
                required property int index
                readonly property real t: [0.14, 0.265, 0.365, 0.505, 0.61, 0.735, 0.85][index] + frond.rhythm * (index % 2 === 0 ? 0.012 : -0.012)
                readonly property real bx: frond.stemX(t)
                readonly property real by: frond.stemY(t)
                readonly property real direction: index % 2 === 0 ? 1 : -1
                readonly property real reach: frond.width * (index === 4 ? 0.21 : 0.31 + (index % 3) * 0.035)
                readonly property real lift: frond.height * (0.13 + (index % 3) * 0.012)
                readonly property real tx: bx + direction * reach
                readonly property real ty: by - lift
                readonly property real fold: frond.height * (0.047 + index % 2 * 0.013)
                readonly property color tone: Qt.lighter(frond.ink, 1.0 + index % 3 * 0.065)
                anchors.fill: parent
                preferredRendererType: Shape.CurveRenderer
                // A short petiole joins the blade to the main stem.
                ShapePath {
                    strokeColor: Qt.lighter(frond.ink, 1.3); strokeWidth: 0.9; fillColor: "transparent"
                    startX: leaf.bx; startY: leaf.by
                    PathQuad { x: leaf.bx + leaf.direction * leaf.reach * 0.2; y: leaf.by - leaf.lift * 0.12; controlX: leaf.bx + leaf.direction * leaf.reach * 0.1; controlY: leaf.by }
                }
                ShapePath {
                    strokeWidth: 0
                    fillGradient: LinearGradient {
                        x1: leaf.tx; y1: leaf.ty; x2: leaf.bx; y2: leaf.by
                        GradientStop { position: 0; color: Qt.lighter(leaf.tone, 1.23) }
                        GradientStop { position: 0.52; color: leaf.tone }
                        GradientStop { position: 1; color: Qt.darker(leaf.tone, 1.16) }
                    }
                    startX: leaf.bx + leaf.direction * leaf.reach * 0.12; startY: leaf.by - leaf.lift * 0.06
                    PathCubic {
                        x: leaf.tx; y: leaf.ty
                        control1X: leaf.bx + leaf.direction * leaf.reach * 0.09; control1Y: leaf.by - leaf.lift * 0.72 - leaf.fold
                        control2X: leaf.tx - leaf.direction * leaf.reach * 0.32; control2Y: leaf.ty + leaf.fold * 0.05
                    }
                    PathCubic {
                        x: leaf.bx + leaf.direction * leaf.reach * 0.12; y: leaf.by - leaf.lift * 0.06
                        control1X: leaf.tx - leaf.direction * leaf.reach * 0.26; control1Y: leaf.ty + leaf.lift * 0.74 + leaf.fold
                        control2X: leaf.bx + leaf.direction * leaf.reach * 0.64; control2Y: leaf.by + leaf.fold * 0.52
                    }
                }
                // The shaded half rolls beneath a fine midrib.
                ShapePath {
                    strokeWidth: 0; fillColor: "#18201d12"
                    startX: leaf.bx + leaf.direction * leaf.reach * 0.12; startY: leaf.by - leaf.lift * 0.06
                    PathQuad { x: leaf.tx; y: leaf.ty; controlX: leaf.bx + leaf.direction * leaf.reach * 0.66; controlY: leaf.by - leaf.lift * 0.34 }
                    PathCubic {
                        x: leaf.bx + leaf.direction * leaf.reach * 0.12; y: leaf.by - leaf.lift * 0.06
                        control1X: leaf.tx - leaf.direction * leaf.reach * 0.26; control1Y: leaf.ty + leaf.lift * 0.74 + leaf.fold
                        control2X: leaf.bx + leaf.direction * leaf.reach * 0.64; control2Y: leaf.by + leaf.fold * 0.52
                    }
                }
                ShapePath {
                    strokeColor: Qt.lighter(leaf.tone, 1.3); strokeWidth: 0.65; fillColor: "transparent"
                    startX: leaf.bx + leaf.direction * leaf.reach * 0.13; startY: leaf.by - leaf.lift * 0.08
                    PathQuad { x: leaf.tx - leaf.direction * leaf.reach * 0.1; y: leaf.ty + leaf.lift * 0.13; controlX: leaf.bx + leaf.direction * leaf.reach * 0.66; controlY: leaf.by - leaf.lift * 0.34 }
                    PathMove { x: leaf.bx + leaf.direction * leaf.reach * 0.47; y: leaf.by - leaf.lift * 0.31 }
                    PathQuad { x: leaf.bx + leaf.direction * leaf.reach * 0.45; y: leaf.by - leaf.lift * 0.67; controlX: leaf.bx + leaf.direction * leaf.reach * 0.4; controlY: leaf.by - leaf.lift * 0.5 }
                    PathMove { x: leaf.bx + leaf.direction * leaf.reach * 0.64; y: leaf.by - leaf.lift * 0.49 }
                    PathQuad { x: leaf.bx + leaf.direction * leaf.reach * 0.78; y: leaf.by - leaf.lift * 0.35; controlX: leaf.bx + leaf.direction * leaf.reach * 0.74; controlY: leaf.by - leaf.lift * 0.4 }
                }
            }
        }
    }
    Frond {
        x: habitat.width * 0.09; y: habitat.floorY - height
        width: habitat.width * 0.21; height: habitat.height * 0.45
        ink: "#344c36"; opacity: 0.78
    }
    Frond {
        x: habitat.width * 0.69; y: habitat.floorY - height + 5
        width: habitat.width * 0.21; height: habitat.height * 0.51
        ink: "#2c4232"; opacity: 0.68; cadence: 8100; rhythm: 1
        transform: Scale { xScale: -1; origin.x: habitat.width * 0.105 }
    }

    // A deep, low stone shelf gives Moss actual ground and the bowl a place.
    Shape {
        id: ground
        x: 0; y: habitat.floorY - 10
        width: habitat.width; height: habitat.height - y
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: 0; fillColor: "#8009120c"
            startX: ground.width * 0.02; startY: 26
            PathCubic { x: ground.width * 0.96; y: 29; control1X: ground.width * 0.32; control1Y: 3; control2X: ground.width * 0.77; control2Y: 1 }
            PathLine { x: ground.width * 0.92; y: ground.height * 0.8 }
            PathCubic { x: ground.width * 0.1; y: ground.height * 0.86; control1X: ground.width * 0.68; control1Y: ground.height * 1.02; control2X: ground.width * 0.28; control2Y: ground.height * 1.01 }
            PathLine { x: ground.width * 0.02; y: 26 }
        }
        ShapePath {
            strokeWidth: 0
            fillGradient: LinearGradient {
                x1: ground.width * 0.18; y1: 0; x2: ground.width * 0.4; y2: ground.height * 0.95
                GradientStop { position: 0; color: "#354533" }
                GradientStop { position: 0.45; color: "#2c3b2d" }
                GradientStop { position: 1; color: "#1d2c23" }
            }
            startX: ground.width * 0.03; startY: 14
            PathCubic { x: ground.width * 0.97; y: 17; control1X: ground.width * 0.2; control1Y: -5; control2X: ground.width * 0.81; control2Y: -10 }
            PathLine { x: ground.width * 0.93; y: ground.height * 0.67 }
            PathCubic { x: ground.width * 0.07; y: ground.height * 0.72; control1X: ground.width * 0.71; control1Y: ground.height * 0.88; control2X: ground.width * 0.28; control2Y: ground.height * 0.92 }
            PathLine { x: ground.width * 0.03; y: 14 }
        }
        ShapePath {
            strokeColor: "#404f37"; strokeWidth: 0.8
            fillGradient: LinearGradient {
                x1: ground.width * 0.2; y1: 0; x2: ground.width * 0.74; y2: 40
                GradientStop { position: 0; color: "#4f5d40" }
                GradientStop { position: 0.6; color: "#425239" }
                GradientStop { position: 1; color: "#344532" }
            }
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
    // The front lip and mineral seams stay inside the existing slab outline.
    Shape {
        id: shelfFinish
        x: ground.x; y: ground.y; width: ground.width; height: ground.height
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: 0; fillColor: "#28312e20"
            startX: shelfFinish.width * 0.035; startY: 17
            PathCubic { x: shelfFinish.width * 0.965; y: 20; control1X: shelfFinish.width * 0.2; control1Y: 48; control2X: shelfFinish.width * 0.86; control2Y: 45 }
            PathLine { x: shelfFinish.width * 0.96; y: 25 }
            PathCubic { x: shelfFinish.width * 0.035; y: 17; control1X: shelfFinish.width * 0.73; control1Y: 54; control2X: shelfFinish.width * 0.22; control2Y: 46 }
        }
        ShapePath {
            strokeColor: "#365d6349"; strokeWidth: 0.8; fillColor: "transparent"
            startX: shelfFinish.width * 0.09; startY: shelfFinish.height * 0.38
            PathCubic { x: shelfFinish.width * 0.31; y: shelfFinish.height * 0.49; control1X: shelfFinish.width * 0.16; control1Y: shelfFinish.height * 0.4; control2X: shelfFinish.width * 0.22; control2Y: shelfFinish.height * 0.52 }
            PathMove { x: shelfFinish.width * 0.62; y: shelfFinish.height * 0.65 }
            PathQuad { x: shelfFinish.width * 0.88; y: shelfFinish.height * 0.48; controlX: shelfFinish.width * 0.75; controlY: shelfFinish.height * 0.58 }
        }
    }
    // Sparse, fixed cushions sit at the planted edges, leaving the walking
    // surface and the finished bowl clear. No random or simulated growth.
    Repeater {
        model: 11
        Rectangle {
            required property int index
            x: habitat.width * (index < 7 ? 0.10 + index * 0.025 : 0.88 + (index - 7) * 0.015)
            y: habitat.floorY + (index % 3) * 2
            width: habitat.width * (0.025 + index % 3 * 0.004)
            height: 3 + index % 3 * 1.5; radius: height / 2
            rotation: -7 + index % 4 * 5
            color: index % 3 === 0 ? "#67724b" : "#51613e"
            opacity: 0.55
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
