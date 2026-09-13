import QtQuick
import QtQuick.Shapes

Item {
    id: creature
    width: 230; height: 200
    property string mood: "content"
    state: "idle"

    // The habitat supplies completed actions. Every property below is visual.
    function perform(action) {
        state = action
        settle.restart()
    }
    Timer { id: settle; interval: 4200; onTriggered: creature.state = "idle" }

    property real lean: 0
    property real sink: 0
    property real stature: 1
    property real headTilt: -8
    property real headDrop: 0
    property real leftArm: 8
    property real rightArm: -10
    property real crownLean: -4
    property real breath: 0
    property real hop: 0
    property real nibble: 0
    property real crownFollow: -hop * 0.6
    readonly property bool resting: state === "sleep"
    readonly property bool eyesClosed: resting || (state === "idle" && mood === "sleepy")
    Behavior on crownFollow { NumberAnimation { duration: 230; easing.type: Easing.OutSine } }

    states: [
        State { name: "idle" },
        State {
            name: "eat"
            PropertyChanges { target: creature; headTilt: 3; headDrop: 4; leftArm: -62; rightArm: 57; crownLean: 4 }
        },
        State {
            name: "sleep"
            PropertyChanges { target: creature; lean: -5; stature: 0.91; sink: 3; headTilt: -19; headDrop: 10; leftArm: -18; rightArm: 20; crownLean: -22 }
        },
        State {
            name: "play"
            PropertyChanges { target: creature; lean: 3; headTilt: 9; leftArm: 30; rightArm: -36; crownLean: 12 }
        },
        State {
            name: "sulk"
            PropertyChanges { target: creature; lean: 5; stature: 0.96; headTilt: 16; headDrop: 9; leftArm: -14; rightArm: 17; crownLean: -18 }
        }
    ]
    transitions: Transition {
        NumberAnimation {
            properties: "lean,sink,stature,headTilt,headDrop,leftArm,rightArm,crownLean"
            duration: 680; easing.type: Easing.InOutSine
        }
    }
    SequentialAnimation on breath {
        running: creature.visible; loops: Animation.Infinite
        NumberAnimation { to: 1; duration: 1900; easing.type: Easing.InOutSine }
        NumberAnimation { to: 0; duration: 2500; easing.type: Easing.InOutSine }
    }
    SequentialAnimation on hop {
        running: creature.visible && creature.state === "play"; loops: Animation.Infinite
        NumberAnimation { to: -2; duration: 170; easing.type: Easing.InOutSine }
        NumberAnimation { to: 8; duration: 330; easing.type: Easing.OutQuad }
        NumberAnimation { to: -1; duration: 440; easing.type: Easing.InQuad }
        NumberAnimation { to: 0; duration: 230; easing.type: Easing.OutSine }
        PauseAnimation { duration: 580 }
    }
    SequentialAnimation on nibble {
        running: creature.visible && creature.state === "eat"; loops: Animation.Infinite
        NumberAnimation { to: 1; duration: 260; easing.type: Easing.InOutSine }
        NumberAnimation { to: 0; duration: 350; easing.type: Easing.InOutSine }
        PauseAnimation { duration: 320 }
    }
    onStateChanged: {
        if (state !== "play") hop = 0
        if (state !== "eat") nibble = 0
    }

    // Small reusable leaves keep all foliage in this one scalable QML file.
    component Leaf: Shape {
        id: leaf
        width: 16; height: 26
        property color tint: "#81935c"
        preferredRendererType: Shape.CurveRenderer
        transformOrigin: Item.Top
        ShapePath {
            strokeWidth: 0; fillColor: leaf.tint
            startX: 8; startY: 0
            PathCubic { x: 15; y: 13; control1X: 13; control1Y: 2; control2X: 17; control2Y: 6 }
            PathCubic { x: 7; y: 26; control1X: 15; control1Y: 19; control2X: 10; control2Y: 23 }
            PathCubic { x: 1; y: 12; control1X: 1; control1Y: 23; control2X: -1; control2Y: 18 }
            PathCubic { x: 8; y: 0; control1X: 0; control1Y: 6; control2X: 4; control2Y: 2 }
        }
    }
    component Foliage: Item {
        property var pieces: [] // x, y, angle, scale, tint; fixed artwork only
        Repeater {
            model: parent.pieces
            Leaf {
                required property var modelData
                x: modelData[0]; y: modelData[1]; rotation: modelData[2]
                scale: modelData[3]; tint: modelData[4]
            }
        }
    }
    component Limb: Shape {
        width: 22; height: 48
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: 0
            fillGradient: LinearGradient {
                x1: 0; y1: 6; x2: 20; y2: 45
                GradientStop { position: 0; color: "#91a36d" }
                GradientStop { position: 1; color: "#617849" }
            }
            startX: 10; startY: 1
            PathCubic { x: 21; y: 32; control1X: 21; control1Y: 3; control2X: 20; control2Y: 22 }
            PathCubic { x: 16; y: 46; control1X: 25; control1Y: 42; control2X: 21; control2Y: 48 }
            PathCubic { x: 2; y: 39; control1X: 8; control1Y: 51; control2X: 0; control2Y: 47 }
            PathCubic { x: 10; y: 1; control1X: -2; control1Y: 27; control2X: 0; control2Y: 5 }
        }
    }

    Rectangle {
        x: 69; y: 185; width: 100; height: 12; radius: 50
        color: "#09130e"; opacity: 0.48 - creature.hop * 0.017
    }
    Item {
        id: sprite
        objectName: "spriteBody"
        width: 230; height: 190
        y: creature.sink - creature.hop
        rotation: creature.lean + creature.breath * (creature.resting ? 0.15 : 0.65)
        transform: Scale {
            origin.x: 115; origin.y: 188
            xScale: 1 + creature.breath * 0.007
            yScale: creature.stature + creature.breath * (creature.resting ? 0.003 : 0.009)
        }
        transformOrigin: Item.Bottom

        // Short planted legs remain behind the rounded, leaf-covered torso.
        Limb { x: 90; y: 151; scale: 0.78; rotation: 3; transformOrigin: Item.Top }
        Limb { x: 119; y: 151; scale: 0.78; rotation: -4; transformOrigin: Item.Top }

        Item {
            id: torso
            x: 84; y: 113; width: 65; height: 61
            Shape {
                anchors.fill: parent; preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    strokeWidth: 0
                    fillGradient: LinearGradient {
                        x1: 16; y1: 0; x2: 50; y2: 64
                        GradientStop { position: 0; color: "#99ab76" }
                        GradientStop { position: 0.6; color: "#80965d" }
                        GradientStop { position: 1; color: "#5f794b" }
                    }
                    startX: 28; startY: 0
                    PathCubic { x: 60; y: 24; control1X: 46; control1Y: -3; control2X: 58; control2Y: 9 }
                    PathCubic { x: 49; y: 59; control1X: 70; control1Y: 45; control2X: 59; control2Y: 56 }
                    PathCubic { x: 8; y: 51; control1X: 31; control1Y: 69; control2X: 12; control2Y: 63 }
                    PathCubic { x: 28; y: 0; control1X: -8; control1Y: 31; control2X: 3; control2Y: 1 }
                }
            }
            Foliage {
                pieces: [
                    [5, 21, -27, 0.9, "#6d854d"], [38, 26, 22, 0.95, "#6d854d"],
                    [20, 25, -10, 1.0, "#8da368"], [10, 10, -26, 0.86, "#9cac71"],
                    [36, 10, 24, 0.88, "#91a567"], [25, 9, 1, 0.95, "#a5b579"]
                ]
            }
        }

        // Arms pivot at the shoulders; eat draws the soft mittens inward.
        Item {
            x: 74; y: 114; width: 22; height: 48
            rotation: creature.leftArm - creature.nibble * 4
            transformOrigin: Item.Top
            Limb { }
            Leaf { x: 1; y: 4; scale: 0.85; rotation: 8; tint: "#9bac73" }
            Leaf { x: 2; y: 19; scale: 0.68; rotation: -9; tint: "#879d63" }
        }
        Item {
            x: 140; y: 112; width: 22; height: 48
            rotation: creature.rightArm + creature.nibble * 4
            transformOrigin: Item.Top
            Limb { }
            Leaf { x: 0; y: 4; scale: 0.78; rotation: -12; tint: "#889f64" }
        }

        // An uneven collar hides the joints and joins the head to its foliage.
        Foliage {
            x: 81; y: 105
            pieces: [
                [-2, 1, 52, 0.83, "#70874e"], [53, 1, -58, 0.82, "#7f9355"],
                [3, 1, 26, 0.86, "#7d9154"], [43, 2, -28, 0.92, "#8c9d5d"],
                [15, 3, 15, 0.88, "#91a367"], [34, 5, -14, 0.95, "#a0ad6e"],
                [25, 0, -5, 0.78, "#82965b"]
            ]
        }

        Item {
            id: head
            objectName: "spriteHead"
            x: 65; y: 37 + creature.headDrop + creature.nibble * 1.4
            width: 101; height: 80
            rotation: creature.headTilt + creature.breath * (creature.resting ? 0.2 : 0.7)
            transformOrigin: Item.Bottom

            Shape {
                anchors.fill: parent; preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    strokeWidth: 0
                    fillGradient: LinearGradient {
                        x1: 25; y1: 8; x2: 77; y2: 83
                        GradientStop { position: 0; color: "#bbc68d" }
                        GradientStop { position: 0.52; color: "#a7b87d" }
                        GradientStop { position: 1; color: "#829860" }
                    }
                    startX: 46; startY: 3
                    PathCubic { x: 94; y: 26; control1X: 69; control1Y: -3; control2X: 86; control2Y: 8 }
                    PathCubic { x: 93; y: 59; control1X: 104; control1Y: 43; control2X: 100; control2Y: 51 }
                    PathCubic { x: 48; y: 79; control1X: 87; control1Y: 75; control2X: 67; control2Y: 80 }
                    PathCubic { x: 4; y: 55; control1X: 19; control1Y: 80; control2X: 7; control2Y: 72 }
                    PathCubic { x: 12; y: 20; control1X: -1; control1Y: 44; control2X: 1; control2Y: 27 }
                    PathCubic { x: 46; y: 3; control1X: 19; control1Y: 4; control2X: 30; control2Y: 5 }
                }
            }

            // The original branching growth survives as the sprite's crown.
            Item {
                x: 47; y: -30; width: 37; height: 43
                rotation: creature.crownLean + creature.crownFollow + creature.breath * 1.8
                transformOrigin: Item.Bottom
                Shape {
                    anchors.fill: parent; preferredRendererType: Shape.CurveRenderer
                    ShapePath {
                        strokeColor: "#8fa66b"; strokeWidth: 4.5; fillColor: "transparent"
                        capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
                        startX: 16; startY: 42
                        PathCubic { x: 21; y: 4; control1X: 10; control1Y: 23; control2X: 23; control2Y: 22 }
                        PathMove { x: 15; y: 27 }
                        PathCubic { x: 2; y: 15; control1X: 12; control1Y: 19; control2X: 4; control2Y: 23 }
                        PathMove { x: 17; y: 32 }
                        PathCubic { x: 33; y: 20; control1X: 21; control1Y: 24; control2X: 30; control2Y: 28 }
                    }
                }
                Rectangle { x: 17; y: 0; width: 8; height: 10; radius: 4; rotation: 23; color: "#c0c999" }
                Rectangle { x: -2; y: 11; width: 8; height: 9; radius: 4; rotation: -28; color: "#b4c18a" }
                Rectangle { x: 29; y: 16; width: 8; height: 9; radius: 4; rotation: 30; color: "#b8c58e" }
            }
            Foliage {
                pieces: [
                    [10, 22, 32, 0.7, "#728b50"], [10, 11, 42, 0.88, "#829759"],
                    [21, 5, 25, 0.82, "#98aa65"], [30, 1, -25, 0.72, "#a7b575"],
                    [40, 1, 64, 0.75, "#91a361"], [49, 0, -59, 0.67, "#aebc7d"],
                    [70, 4, -65, 0.63, "#a2b273"], [19, 16, 5, 0.58, "#afbd79"]
                ]
            }

            // Dark eyes sit inside moss-green rims, with small soft catchlights.
            Row {
                x: 32; y: 39; spacing: 17
                Repeater {
                    model: 2
                    Item {
                        required property int index
                        width: 18; height: 21
                        y: index === 0 ? 2 : 0
                        Rectangle { anchors.centerIn: parent; width: 20; height: 22; radius: 11; color: "#91a669"; opacity: 0.65 }
                        Rectangle {
                            anchors.centerIn: parent
                            width: 15; height: creature.eyesClosed ? 2.5 : creature.state === "sulk" ? 12 : 17
                            radius: 8; color: "#526f48"
                            Behavior on height { NumberAnimation { duration: 300; easing.type: Easing.InOutSine } }
                            Rectangle { anchors.centerIn: parent; width: 10.5; height: Math.max(2, parent.height - 4); radius: 6; color: "#182f26" }
                            Rectangle { x: 3.5; y: 3; width: 3.4; height: 3.4; radius: 2; color: "#dce0b8"; opacity: creature.eyesClosed ? 0 : 0.8 }
                            Rectangle { x: 10; y: 12; width: 1.6; height: 1.6; radius: 1; color: "#92b394"; opacity: creature.eyesClosed || creature.state === "sulk" ? 0 : 0.5 }
                        }
                    }
                }
            }
            Rectangle {
                x: 59; y: 67; width: 6; height: 1.4; radius: 1
                rotation: -16; color: "#647d4b"; opacity: 0.65
            }
        }
    }
}
