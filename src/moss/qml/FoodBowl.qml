import QtQuick
import QtQuick.Controls
import QtQuick.Shapes

// Presentation only. The harness owns commit count and consumption; this item
// merely turns the projected count into a small object in Moss's habitat.
Item {
    id: bowl
    property int commitCount: 0
    property bool eating: false
    readonly property int tokenCount: Math.min(Math.max(commitCount, 0), 7)
    readonly property real abundanceBoost: Math.min(0.12, Math.max(0, commitCount - tokenCount) * 0.01)

    implicitWidth: 102
    implicitHeight: 76

    Rectangle {
        x: bowl.width * 0.13; y: bowl.height * 0.56
        width: bowl.width * 0.74; height: bowl.height * 0.12
        radius: height / 2
        color: "#08110d"; opacity: 0.5
    }

    Item {
        id: vessel
        x: bowl.width * 0.04; y: bowl.height * 0.12
        width: bowl.width * 0.92; height: bowl.height * 0.52
        transformOrigin: Item.Bottom
        scale: bowl.eating ? 1.025 : 1.0
        Behavior on scale { NumberAnimation { duration: 280; easing.type: Easing.OutCubic } }

        // Back rim and cavity establish the depth the food sits inside.
        Rectangle {
            x: vessel.width * 0.08; y: vessel.height * 0.06
            width: vessel.width * 0.84; height: vessel.height * 0.36
            radius: height / 2
            color: "#78634a"; border.width: 1; border.color: "#8f7957"
        }
        Rectangle {
            x: vessel.width * 0.13; y: vessel.height * 0.11
            width: vessel.width * 0.74; height: vessel.height * 0.23
            radius: height / 2
            color: "#20271e"; border.width: 1; border.color: "#3e4734"
        }
        Rectangle {
            x: vessel.width * 0.16; y: vessel.height * 0.13
            width: vessel.width * 0.68; height: vessel.height * 0.17
            radius: height / 2
            color: "#a7b584"; opacity: bowl.eating ? 0.12 : 0
            Behavior on opacity { NumberAnimation { duration: 320; easing.type: Easing.InOutSine } }
        }

        // Commit food: deterministic botanical seed pods. The visual count is
        // capped, while the label below always preserves the authoritative total.
        Item {
            id: nutrientBed
            x: vessel.width * 0.14; y: vessel.height * 0.015
            width: vessel.width * 0.72; height: vessel.height * 0.34
            clip: true
            Repeater {
                model: bowl.tokenCount
                Shape {
                    id: pod
                    required property int index
                    readonly property real spreadX: 0.04 + ((index * 37) % 71) / 100
                    readonly property real settleY: 0.08 + ((index * 23) % 28) / 100
                    width: nutrientBed.width * 0.15
                    height: nutrientBed.height * 0.72
                    x: nutrientBed.width * spreadX
                    y: nutrientBed.height * settleY
                    rotation: -26 + ((index * 47) % 53)
                    scale: 0.86 + ((index * 19) % 16) / 100 + bowl.abundanceBoost
                    preferredRendererType: Shape.CurveRenderer
                    ShapePath {
                        strokeColor: "#92965f"; strokeWidth: 0.7
                        fillColor: index % 3 === 0 ? "#b6b67b" : index % 3 === 1 ? "#9eaa6f" : "#c0b981"
                        startX: pod.width * 0.5; startY: 0
                        PathCubic {
                            x: pod.width; y: pod.height * 0.48
                            control1X: pod.width * 0.84; control1Y: pod.height * 0.08
                            control2X: pod.width * 1.05; control2Y: pod.height * 0.28
                        }
                        PathCubic {
                            x: pod.width * 0.5; y: pod.height
                            control1X: pod.width * 0.95; control1Y: pod.height * 0.72
                            control2X: pod.width * 0.71; control2Y: pod.height * 0.94
                        }
                        PathCubic {
                            x: 0; y: pod.height * 0.48
                            control1X: pod.width * 0.28; control1Y: pod.height * 0.94
                            control2X: pod.width * 0.05; control2Y: pod.height * 0.72
                        }
                        PathCubic {
                            x: pod.width * 0.5; y: 0
                            control1X: -pod.width * 0.05; control1Y: pod.height * 0.28
                            control2X: pod.width * 0.18; control2Y: pod.height * 0.08
                        }
                    }
                    ShapePath {
                        strokeColor: "#6d754d"; strokeWidth: 0.65; fillColor: "transparent"
                        startX: pod.width * 0.5; startY: pod.height * 0.13
                        PathLine { x: pod.width * 0.5; y: pod.height * 0.82 }
                    }
                }
            }
        }

        // The stone body occludes the lower part of the pods so they read as
        // sitting inside the bowl instead of floating in front of it.
        Shape {
            x: 0; y: vessel.height * 0.19
            width: vessel.width; height: vessel.height * 0.76
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: "#8d7858"; strokeWidth: 1
                fillGradient: LinearGradient {
                    x1: vessel.width * 0.18; y1: 0
                    x2: vessel.width * 0.72; y2: vessel.height * 0.65
                    GradientStop { position: 0; color: "#826b4f" }
                    GradientStop { position: 0.58; color: "#66513d" }
                    GradientStop { position: 1; color: "#4d3e32" }
                }
                startX: vessel.width * 0.08; startY: 0
                PathCubic {
                    x: vessel.width * 0.92; y: 0
                    control1X: vessel.width * 0.28; control1Y: vessel.height * 0.13
                    control2X: vessel.width * 0.72; control2Y: vessel.height * 0.13
                }
                PathCubic {
                    x: vessel.width * 0.72; y: vessel.height * 0.69
                    control1X: vessel.width * 0.9; control1Y: vessel.height * 0.35
                    control2X: vessel.width * 0.82; control2Y: vessel.height * 0.61
                }
                PathCubic {
                    x: vessel.width * 0.28; y: vessel.height * 0.69
                    control1X: vessel.width * 0.61; control1Y: vessel.height * 0.79
                    control2X: vessel.width * 0.39; control2Y: vessel.height * 0.79
                }
                PathCubic {
                    x: vessel.width * 0.08; y: 0
                    control1X: vessel.width * 0.18; control1Y: vessel.height * 0.61
                    control2X: vessel.width * 0.1; control2Y: vessel.height * 0.35
                }
            }
            ShapePath {
                strokeColor: "#a18a63"; strokeWidth: 1.2; fillColor: "transparent"
                startX: vessel.width * 0.09; startY: 1
                PathCubic {
                    x: vessel.width * 0.91; y: 1
                    control1X: vessel.width * 0.31; control1Y: vessel.height * 0.13
                    control2X: vessel.width * 0.69; control2Y: vessel.height * 0.13
                }
            }
        }

        // Moss stays on the exterior: the empty cavity remains unmistakably empty.
        Rectangle {
            x: vessel.width * 0.19; y: vessel.height * 0.68
            width: vessel.width * 0.17; height: 3; radius: 2
            color: "#65734b"; opacity: 0.72; rotation: -5
        }
        Rectangle {
            x: vessel.width * 0.63; y: vessel.height * 0.61
            width: vessel.width * 0.1; height: 2; radius: 2
            color: "#738056"; opacity: 0.54; rotation: 7
        }
    }

    Label {
        objectName: "bowlLabel"
        anchors.horizontalCenter: parent.horizontalCenter
        y: bowl.height * 0.72
        textFormat: Text.PlainText
        text: bowl.commitCount + (bowl.commitCount === 1 ? " commit" : " commits")
        color: "#b7b69b"; font.pixelSize: 11
    }
}
