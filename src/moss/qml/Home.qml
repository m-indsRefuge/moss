import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: home
    required property QtObject bridge
    width: 720; height: 820
    minimumWidth: 540; minimumHeight: 700
    visible: true
    title: "Moss · " + bridge.repoPath
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

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            Label { text: bridge.name.toUpperCase(); font.pixelSize: 25; font.letterSpacing: 5 }
            Item { Layout.fillWidth: true }
            Label { text: "COMMITS ARE FOOD"; color: "#96aa91"; font.pixelSize: 11; font.letterSpacing: 2 }
        }
        Label {
            Layout.fillWidth: true
            text: bridge.repoPath; textFormat: Text.PlainText
            wrapMode: Text.WrapAnywhere; color: "#96aa91"; font.pixelSize: 12
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 210
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom; anchors.bottomMargin: 24
                width: parent.width * 0.82; height: 52; radius: width / 2
                color: "#23362a"
            }
            Creature {
                id: creature
                objectName: "creature"
                anchors.centerIn: parent
                visible: bridge.ready
                mood: bridge.mood
            }
            Label {
                anchors.centerIn: parent; visible: !bridge.ready
                text: bridge.busy ? "Opening home…" : "Moss could not be loaded"
                color: "#96aa91"
            }
            Column {
                anchors.right: parent.right; anchors.rightMargin: 24
                anchors.bottom: parent.bottom; anchors.bottomMargin: 30
                spacing: 6
                Rectangle {
                    width: 60; height: 23; radius: 9; color: "#786246"
                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: -4; spacing: 4
                        Repeater {
                            model: bridge.ready ? Math.min(bridge.bowl, 5) : 0
                            Rectangle { width: 7; height: 7; radius: 2; color: "#c5c58a"; rotation: 20 }
                        }
                    }
                }
                Label { text: bridge.ready ? bridge.bowl + " commits" : "—"; color: "#bac5a6"; font.pixelSize: 12 }
            }
            Label {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                text: bridge.ready ? bridge.mood + " · " + creature.state : ""
                textFormat: Text.PlainText; color: "#b0c299"
            }
        }

        GridLayout {
            Layout.fillWidth: true; columns: 3; rowSpacing: 8; columnSpacing: 14
            Label { text: "Hunger"; color: "#b0c299" }
            ProgressBar { Layout.fillWidth: true; value: bridge.hunger; visible: bridge.ready }
            Label { text: bridge.ready ? Math.round(bridge.hunger * 100) + "%" : "—" }
            Label { text: "Energy"; color: "#b0c299" }
            ProgressBar { Layout.fillWidth: true; value: bridge.energy; visible: bridge.ready }
            Label { text: bridge.ready ? Math.round(bridge.energy * 100) + "%" : "—" }
        }
        Label {
            Layout.fillWidth: true
            text: bridge.thought; textFormat: Text.PlainText
            visible: text.length > 0; wrapMode: Text.Wrap; font.pixelSize: 17
        }
        Label {
            Layout.fillWidth: true
            text: "Wish · " + bridge.wish; textFormat: Text.PlainText
            visible: bridge.wish.length > 0; wrapMode: Text.Wrap; color: "#bac5a6"
        }
        Label { text: "DIARY"; font.pixelSize: 11; font.letterSpacing: 3; color: "#96aa91" }
        ScrollView {
            Layout.fillWidth: true; Layout.preferredHeight: 100
            clip: true
            TextArea {
                readOnly: true; selectByMouse: true
                text: bridge.diary || (bridge.ready ? "No diary entries yet." : "")
                textFormat: TextEdit.PlainText; wrapMode: TextEdit.Wrap
                color: "#d4ddc7"; background: null
            }
        }
        Label {
            Layout.fillWidth: true
            text: "Last tick · " + (bridge.lastTick || "—")
            textFormat: Text.PlainText; color: "#96aa91"; font.pixelSize: 11
            wrapMode: Text.WrapAnywhere
        }
        Label {
            Layout.fillWidth: true
            text: bridge.repoStatus + "  /  " + bridge.brainStatus
            color: "#b0c299"; font.pixelSize: 12; wrapMode: Text.Wrap
        }
        Label {
            Layout.fillWidth: true
            visible: bridge.error.length > 0
            text: bridge.error; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: "#efb38e"
        }
        RowLayout {
            Layout.fillWidth: true
            BusyIndicator { running: bridge.busy; visible: running; Layout.preferredWidth: 30; Layout.preferredHeight: 30 }
            Label {
                Layout.fillWidth: true; text: bridge.activity
                wrapMode: Text.Wrap; color: "#96aa91"; font.pixelSize: 12
            }
            Button {
                objectName: "tickButton"
                text: bridge.ready ? "Live a tick" : "Open home"
                enabled: !bridge.busy && !bridge.closing
                onClicked: bridge.ready ? bridge.requestTick() : bridge.open()
            }
        }
    }
}
