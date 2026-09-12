import QtQuick
import QtQuick.Shapes

Item {
    id: creature
    width: 230; height: 200
    property string mood: "content"
    state: "idle"

    // All motion is local presentation. The existing action contract is unchanged.
    function perform(action) {
        state = action
        settle.restart()
    }
    Timer { id: settle; interval: 4200; onTriggered: creature.state = "idle" }

    property real girth: 1
    property real stature: 1
    property real lean: -2
    property real sink: 0
    property real crownLean: -6
    property real faceShift: 0
    property real breath: 0
    property real hop: 0
    readonly property bool resting: state === "sleep"
    readonly property real breathing: resting ? 0.25 : state === "eat" ? 1.8 : 1

    states: [
        State { name: "idle" },
        State {
            name: "eat"
            PropertyChanges { target: creature; girth: 1.08; stature: 1.04; lean: 2; sink: -3; crownLean: 5 }
        },
        State {
            name: "sleep"
            PropertyChanges { target: creature; girth: 1.12; stature: 0.70; lean: -7; sink: 7; crownLean: -37 }
        },
        State {
            name: "play"
            PropertyChanges { target: creature; girth: 0.95; stature: 1.06; lean: 5; crownLean: 16 }
        },
        State {
            name: "sulk"
            PropertyChanges { target: creature; girth: 0.94; stature: 0.86; lean: -15; sink: 5; crownLean: -29; faceShift: -16 }
        }
    ]
    transitions: Transition {
        NumberAnimation {
            properties: "girth,stature,lean,sink,crownLean,faceShift"
            duration: 680; easing.type: Easing.InOutSine
        }
    }
    SequentialAnimation on breath {
        running: creature.visible; loops: Animation.Infinite
        NumberAnimation { to: 1; duration: 1900; easing.type: Easing.InOutSine }
        NumberAnimation { to: 0; duration: 2400; easing.type: Easing.InOutSine }
    }
    SequentialAnimation on hop {
        running: creature.visible && creature.state === "play"
        loops: Animation.Infinite
        NumberAnimation { to: 11; duration: 320; easing.type: Easing.OutQuad }
        NumberAnimation { to: 0; duration: 460; easing.type: Easing.InQuad }
        PauseAnimation { duration: 520 }
    }
    onStateChanged: { if (state !== "play") hop = 0 }

    Rectangle {
        x: 35; y: 171; width: 166; height: 17; radius: 83
        color: "#09130e"; opacity: 0.42 - creature.hop * 0.012
    }
    Item {
        id: growth
        x: 24; y: 33 + creature.sink - creature.hop
        width: 182; height: 148
        rotation: creature.lean + creature.breath * (creature.resting ? 0.15 : 0.8)
        transformOrigin: Item.Bottom
        transform: Scale {
            origin.x: 91; origin.y: 144
            xScale: creature.girth + creature.breath * 0.016 * creature.breathing + creature.hop * 0.002
            yScale: creature.stature + creature.breath * 0.019 * creature.breathing - creature.hop * 0.003
        }

        // An uneven basal mass, with a low left shelf and a taller right fold.
        Shape {
            anchors.fill: parent
            ShapePath {
                strokeWidth: 0
                fillGradient: LinearGradient {
                    x1: 40; y1: 15; x2: 130; y2: 145
                    GradientStop { position: 0; color: "#9ba878" }
                    GradientStop { position: 0.5; color: "#798957" }
                    GradientStop { position: 1; color: "#465d40" }
                }
                startX: 8; startY: 119
                PathCubic { x: 34; y: 58; control1X: -2; control1Y: 92; control2X: 17; control2Y: 79 }
                PathCubic { x: 85; y: 34; control1X: 44; control1Y: 22; control2X: 62; control2Y: 52 }
                PathCubic { x: 138; y: 20; control1X: 107; control1Y: 10; control2X: 113; control2Y: 7 }
                PathCubic { x: 167; y: 83; control1X: 156; control1Y: 24; control2X: 150; control2Y: 67 }
                PathCubic { x: 167; y: 128; control1X: 191; control1Y: 104; control2X: 174; control2Y: 113 }
                PathCubic { x: 112; y: 144; control1X: 160; control1Y: 152; control2X: 139; control2Y: 133 }
                PathCubic { x: 54; y: 145; control1X: 87; control1Y: 161; control2X: 82; control2Y: 140 }
                PathCubic { x: 8; y: 119; control1X: 26; control1Y: 151; control2X: 28; control2Y: 129 }
            }
            // A broad, pale lichen plate grows over the shaded basal fold.
            ShapePath {
                strokeWidth: 0; fillColor: "#a1af7d"
                startX: 20; startY: 88
                PathCubic { x: 46; y: 52; control1X: 28; control1Y: 67; control2X: 24; control2Y: 52 }
                PathCubic { x: 100; y: 30; control1X: 74; control1Y: 61; control2X: 79; control2Y: 26 }
                PathCubic { x: 140; y: 28; control1X: 111; control1Y: 6; control2X: 134; control2Y: 19 }
                PathCubic { x: 111; y: 69; control1X: 147; control1Y: 43; control2X: 119; control2Y: 56 }
                PathCubic { x: 59; y: 96; control1X: 105; control1Y: 90; control2X: 82; control2Y: 75 }
                PathCubic { x: 20; y: 88; control1X: 43; control1Y: 113; control2X: 32; control2Y: 85 }
            }
            // A second curled edge makes the silhouette layered, not outlined.
            ShapePath {
                strokeWidth: 0; fillColor: "#b5bc8c"
                startX: 35; startY: 63
                PathCubic { x: 85; y: 45; control1X: 49; control1Y: 40; control2X: 57; control2Y: 66 }
                PathCubic { x: 130; y: 22; control1X: 111; control1Y: 8; control2X: 116; control2Y: 20 }
                PathCubic { x: 92; y: 55; control1X: 119; control1Y: 29; control2X: 121; control2Y: 43 }
                PathCubic { x: 35; y: 63; control1X: 68; control1Y: 77; control2X: 59; control2Y: 55 }
            }
        }

        // A forked growth scar echoes branching without becoming a Git icon.
        Item {
            x: 79; y: -16; width: 50; height: 63
            rotation: creature.crownLean + creature.breath * (creature.resting ? 0.5 : 2.5)
            transformOrigin: Item.Bottom
            Shape {
                anchors.fill: parent
                ShapePath {
                    strokeWidth: 0; fillColor: "#7c9164"
                    startX: 27; startY: 62
                    PathCubic { x: 10; y: 22; control1X: 29; control1Y: 43; control2X: 9; control2Y: 45 }
                    PathCubic { x: 15; y: 15; control1X: 0; control1Y: 9; control2X: 13; control2Y: 3 }
                    PathLine { x: 24; y: 36 }
                    PathCubic { x: 31; y: 11; control1X: 29; control1Y: 24; control2X: 22; control2Y: 13 }
                    PathCubic { x: 38; y: 18; control1X: 37; control1Y: 4; control2X: 43; control2Y: 12 }
                    PathLine { x: 31; y: 41 }
                    PathCubic { x: 42; y: 30; control1X: 41; control1Y: 43; control2X: 34; control2Y: 30 }
                    PathCubic { x: 49; y: 38; control1X: 47; control1Y: 23; control2X: 55; control2Y: 31 }
                    PathCubic { x: 34; y: 63; control1X: 45; control1Y: 51; control2X: 30; control2Y: 46 }
                    PathLine { x: 27; y: 62 }
                }
            }
            Rectangle { x: 8; y: 12; width: 8; height: 5; radius: 3; rotation: -22; color: "#c0c59a" }
            Rectangle { x: 29; y: 9; width: 8; height: 4; radius: 3; rotation: -35; color: "#c0c59a" }
        }

        // Recessed sensory pores; unknown moods retain the neutral expression.
        Item {
            x: 95 + creature.faceShift; y: 86; opacity: creature.state === "sulk" ? 0.55 : 0.9
            Behavior on opacity { NumberAnimation { duration: 600 } }
            Rectangle { x: -4; y: -3; width: 17; height: 13; radius: 7; color: "#536a47"; rotation: -18 }
            Rectangle {
                x: 0; y: 0; width: 5; height: creature.resting || creature.mood === "sleepy" ? 2 : 5
                radius: 3; color: "#1c3024"; rotation: -15
            }
            Rectangle {
                x: 25; y: -4; width: 4; height: creature.resting || creature.mood === "sleepy" ? 2 : 6
                radius: 3; color: "#203729"; rotation: 8
            }
        }

        // A short pulse through the growth seams expresses the saved eat action.
        // These marks are not an invented count of food or pending Git activity.
        Shape {
            anchors.fill: parent
            opacity: creature.state === "eat" ? 0.25 + creature.breath * 0.65 : 0
            Behavior on opacity { NumberAnimation { duration: 500 } }
            ShapePath {
                fillColor: "transparent"; strokeColor: "#d3c795"; strokeWidth: 2
                capStyle: ShapePath.RoundCap
                startX: 44; startY: 122
                PathCubic { x: 68; y: 91; control1X: 57; control1Y: 124; control2X: 60; control2Y: 104 }
                PathCubic { x: 97; y: 78; control1X: 78; control1Y: 85; control2X: 92; control2Y: 89 }
                PathMove { x: 68; y: 91 }
                PathLine { x: 54; y: 79 }
            }
        }
    }
}
