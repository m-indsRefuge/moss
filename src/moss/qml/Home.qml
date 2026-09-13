import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: home
    required property QtObject bridge
    property bool historyOpen: false
    property bool detailsOpen: false
    width: 800; height: 900
    minimumWidth: 540; minimumHeight: 700
    visible: true
    title: bridge.name + " · " + bridge.repoName
    color: "#111d19"
    font.family: "Segoe UI"
    palette.text: "#e0e8d6"
    palette.windowText: "#e0e8d6"
    palette.button: "#314a37"
    palette.buttonText: "#e0e8d6"
    palette.highlight: "#9bb977"

    onClosing: function(close) {
        close.accepted = false
        bridge.requestClose()
    }
    Connections {
        target: bridge
        function onTickCompleted(action) { creature.perform(action) }
    }
    component Copy: Label {
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
        color: "#d4ddc7"
    }
    component Small: Copy { color: "#96aa91"; font.pixelSize: 12 }
    component Meter: ColumnLayout {
        id: meter
        required property string caption
        required property real level
        required property bool known
        spacing: 9
        RowLayout {
            Layout.fillWidth: true
            Small { text: meter.caption; Layout.fillWidth: true }
            Copy { text: meter.known ? Math.round(meter.level * 100) + "%" : "—"; font.pixelSize: 12 }
        }
        ProgressBar {
            Layout.fillWidth: true
            value: meter.level
            background: Rectangle { implicitHeight: 5; color: "#263a2e"; radius: 3 }
            contentItem: Item {
                implicitHeight: 5
                Rectangle { width: parent.width * meter.level; height: 5; radius: 3; color: "#9caf7a"; visible: meter.known }
            }
        }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 28; spacing: 14
        RowLayout {
            Layout.fillWidth: true
            Copy { text: bridge.name.toUpperCase(); Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap; font.pixelSize: 27; font.letterSpacing: 5 }
            Small { text: "COMMITS ARE FOOD"; font.pixelSize: 10; font.letterSpacing: 2 }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 9
            Rectangle { width: 5; height: 5; radius: 3; color: bridge.hasTick && bridge.lastCommitAt ? "#9caf7a" : "#ac9165" }
            Copy { text: bridge.repoName; font.pixelSize: 13; Layout.maximumWidth: parent.width * 0.4; elide: Text.ElideRight; wrapMode: Text.NoWrap }
            Small {
                Layout.fillWidth: true; text: bridge.repoPath; elide: Text.ElideMiddle; wrapMode: Text.NoWrap
                ToolTip.visible: repoHover.hovered; ToolTip.text: bridge.repoPath
                HoverHandler { id: repoHover }
            }
        }
        ScrollView {
            id: page
            objectName: "habitatScroll"
            Layout.fillWidth: true; Layout.fillHeight: true
            contentWidth: availableWidth; clip: true
            ColumnLayout {
                width: page.availableWidth; spacing: 18
                Item {
                    id: habitat
                    Layout.fillWidth: true; Layout.preferredHeight: 300
                    Rectangle {
                        x: parent.width * 0.05; y: 5; width: parent.width * 0.9; height: 275; radius: 135
                        border.width: 1; border.color: "#2b4134"
                        gradient: Gradient { GradientStop { position: 0; color: "#182b23" } GradientStop { position: 1; color: "#12221b" } }
                    }
                    Rectangle { x: parent.width * 0.19; y: 28; width: parent.width * 0.45; height: 1; color: "#314636"; opacity: 0.5 }
                    Small { x: parent.width * 0.16; y: 46; text: "REPOSITORY HABITAT"; font.pixelSize: 9; font.letterSpacing: 2; color: "#637e64" }
                    Repeater {
                        model: 2
                        Item {
                            required property int index
                            x: habitat.width * (index === 0 ? 0.14 : 0.83); y: 168
                            rotation: index === 0 ? -12 : 14
                            Rectangle { width: 2; height: 70; color: "#385039" }
                            Repeater {
                                model: 4
                                Rectangle {
                                    required property int index
                                    x: index % 2 ? -18 : 1; y: 10 + index * 12
                                    width: 21; height: 9; radius: 5
                                    rotation: index % 2 ? 25 : -25; color: "#344b34"
                                }
                            }
                        }
                    }
                    Rectangle { x: parent.width * 0.1; y: 228; width: parent.width * 0.8; height: 49; radius: width / 2; color: "#17241b" }
                    Rectangle { x: parent.width * 0.105; y: 218; width: parent.width * 0.79; height: 40; radius: width / 2; color: "#2c4030"; border.color: "#3b5037" }
                    Creature {
                        id: creature; objectName: "creature"
                        x: (parent.width - width) / 2 - 18; y: 45
                        visible: bridge.ready; mood: bridge.mood
                    }
                    Small { anchors.centerIn: parent; visible: !bridge.ready; text: bridge.busy ? "Opening home…" : "Moss could not be loaded" }
                    Column {
                        x: parent.width * 0.73; y: 213; width: 84; spacing: 7
                        Rectangle {
                            width: 68; height: 30; radius: 13; color: "#806647"; border.color: "#9b8056"
                            Rectangle { x: 4; y: 2; width: 60; height: 10; radius: 5; color: "#443e2b" }
                            Row {
                                anchors.horizontalCenter: parent.horizontalCenter; y: -1; spacing: 3
                                Repeater {
                                    model: bridge.ready ? Math.min(bridge.bowl, 5) : 0
                                    Rectangle { width: 7; height: 7; radius: 2; color: "#c5c58a"; rotation: 20 }
                                }
                            }
                        }
                        Small { objectName: "bowlLabel"; text: bridge.ready ? bridge.bowl + (bridge.bowl === 1 ? " commit" : " commits") : "—" }
                    }
                    Copy {
                        anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom
                        text: bridge.ready ? bridge.mood + " · " + creature.state : ""
                        color: "#b0c299"; font.pixelSize: 13
                    }
                }
                Small { Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; text: "Wish · " + bridge.wish; visible: bridge.wish.length > 0 }
                RowLayout {
                    Layout.fillWidth: true; spacing: 34
                    Meter { Layout.fillWidth: true; caption: "Hunger"; level: bridge.hunger; known: bridge.ready }
                    Meter { Layout.fillWidth: true; caption: "Energy"; level: bridge.energy; known: bridge.ready }
                }
                Small {
                    objectName: "mealSummary"; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; visible: bridge.hasTick
                    text: "Last tick · " + bridge.commitsArrived + " arrived in the bowl · " + bridge.commitsEatenThisTick + " eaten"
                }
                Copy { objectName: "thoughtLabel"; Layout.fillWidth: true; text: bridge.thought; visible: text.length > 0; font.pixelSize: 17 }
                Rectangle { Layout.fillWidth: true; height: 1; color: "#2b3b2d" }
                RowLayout {
                    Layout.fillWidth: true
                    Small { Layout.fillWidth: true; text: "FIELD NOTES"; font.pixelSize: 10; font.letterSpacing: 3 }
                    ToolButton {
                        objectName: "historyButton"; visible: bridge.diaryEntries.length > 1
                        text: home.historyOpen ? "Close earlier notes" : "Earlier notes (" + (bridge.diaryEntries.length - 1) + ")"
                        font.pixelSize: 12; onClicked: home.historyOpen = !home.historyOpen
                    }
                }
                Copy {
                    objectName: "latestDiary"; Layout.fillWidth: true; font.pixelSize: 16; lineHeight: 1.25
                    text: bridge.diaryEntries.length ? bridge.diaryEntries[0] : (bridge.ready ? "The first page is still waiting." : "")
                }
                ColumnLayout {
                    objectName: "diaryHistory"; Layout.fillWidth: true; visible: home.historyOpen && bridge.diaryEntries.length > 1; spacing: 14
                    Repeater {
                        model: bridge.diaryEntries.slice(1)
                        Copy { required property string modelData; Layout.fillWidth: true; text: modelData; color: "#aabb9e"; lineHeight: 1.2 }
                    }
                }
                Small {
                    objectName: "lifetimeSummary"; Layout.fillWidth: true; visible: bridge.ready
                    text: "Life here · " + bridge.commitsEaten + " commits eaten · " + bridge.sulks + " sulks · longest quiet spell " + bridge.longestNeglectDays + " days"
                }
                ToolButton {
                    objectName: "detailsButton"; text: home.detailsOpen ? "Close habitat details" : "Habitat details"
                    font.pixelSize: 12; onClicked: home.detailsOpen = !home.detailsOpen
                }
                ColumnLayout {
                    objectName: "habitatDetails"; Layout.fillWidth: true; visible: home.detailsOpen; spacing: 9
                    Small { Layout.fillWidth: true; text: "Brain · " + bridge.brainLabel }
                    Small { Layout.fillWidth: true; text: "Last decision · " + bridge.brainStatus + (bridge.hasTick ? " · " + bridge.decisionAttempts + " attempts" : "") }
                    Small { Layout.fillWidth: true; text: "Git · " + bridge.repoStatus }
                    Small { Layout.fillWidth: true; text: "Last observed commit · " + (bridge.lastCommitAt || "Not available this visit"); wrapMode: Text.WrapAnywhere }
                    Small { Layout.fillWidth: true; visible: bridge.hasTick; text: "Scene at last tick · " + (bridge.isNight ? "night" : "day") + " (UTC) · " + bridge.hoursQuiet.toFixed(1) + " hours quiet" }
                    Small {
                        Layout.fillWidth: true; visible: bridge.hasTick && !bridge.lastCommitAt
                        text: "Without a commit timestamp, quiet time is measured from the previous tick. Git sensing cannot distinguish empty history from failure."
                    }
                    Small { Layout.fillWidth: true; text: "State as of · " + (bridge.lastTick || "—"); wrapMode: Text.WrapAnywhere }
                    Small { Layout.fillWidth: true; text: "Home file · " + bridge.statePath; wrapMode: Text.WrapAnywhere }
                    Small { Layout.fillWidth: true; text: "Use one Moss process per home. No background ticks." }
                }
                Item { Layout.preferredHeight: 4 }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: "#2b3b2d" }
        Copy { objectName: "errorLabel"; Layout.fillWidth: true; visible: bridge.error.length > 0; text: bridge.error; color: "#efb38e" }
        RowLayout {
            Layout.fillWidth: true; spacing: 16
            BusyIndicator { running: bridge.busy; visible: running; Layout.preferredWidth: 28; Layout.preferredHeight: 28 }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 5
                Copy {
                    objectName: "brainSummary"; Layout.fillWidth: true; font.pixelSize: 12
                    text: bridge.hasTick ? bridge.brainStatus : "Selected brain · " + bridge.brainLabel
                    color: bridge.usedFallback ? "#d5b786" : "#b0c299"
                }
                Small { Layout.fillWidth: true; text: bridge.activity }
            }
            Button {
                objectName: "tickButton"; Layout.preferredWidth: 126; Layout.preferredHeight: 44
                text: bridge.busy ? "Working…" : bridge.ready ? "Live a tick" : "Open home"
                enabled: !bridge.busy && !bridge.closing
                onClicked: bridge.ready ? bridge.requestTick() : bridge.open()
            }
        }
    }
}
