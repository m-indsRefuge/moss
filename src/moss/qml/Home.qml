import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Shapes

ApplicationWindow {
    id: home
    required property QtObject bridge
    property bool historyOpen: false
    property bool detailsOpen: false
    readonly property bool wide: width >= 900
    readonly property real pageMargin: wide ? 36 : 24
    readonly property real regionGap: wide ? 38 : 30
    readonly property real compactGardenHeight: 455
    width: 1020; height: 800
    minimumWidth: 540; minimumHeight: 700
    visible: true
    title: bridge.name + " · " + bridge.repoName
    color: "#111d17"
    font.family: "Segoe UI"
    palette.text: "#dce0cd"
    palette.windowText: "#dce0cd"
    palette.button: "#2d4130"
    palette.buttonText: "#dce0cd"
    palette.highlight: "#a5b47e"

    onClosing: function(close) {
        close.accepted = false
        bridge.requestClose()
    }
    Connections {
        target: bridge
        function onTickCompleted(action) { habitat.perform(action) }
    }
    component Copy: Label {
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
        color: "#dce0cd"
        font.pixelSize: 14
    }
    component Small: Copy { color: "#a1ac96"; font.pixelSize: 12 }
    component Eyebrow: Small { font.pixelSize: 10; font.letterSpacing: 2.4; color: "#a6af8c" }
    component QuietButton: ToolButton {
        font.pixelSize: 12
        padding: 8
        contentItem: Copy { text: parent.text; font: parent.font; color: "#b2ba9f"; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { color: parent.down ? "#293b2b" : parent.hovered ? "#213326" : "transparent"; radius: 3 }
    }
    component Meter: ColumnLayout {
        id: meter
        required property string caption
        required property real level
        required property bool known
        required property color accent
        required property color accentDeep
        spacing: 8
        RowLayout {
            Layout.fillWidth: true
            Small {
                text: meter.caption.toUpperCase(); Layout.fillWidth: true
                font.pixelSize: 10; font.letterSpacing: 1.15; color: "#aab49a"
            }
            Small {
                text: meter.known ? Math.round(meter.level * 100) + "%" : "—"
                font.pixelSize: 11; font.weight: Font.Medium
                color: meter.known ? meter.accent : "#778174"
            }
        }
        Rectangle {
            id: meterRail; objectName: "meterRail"
            Layout.fillWidth: true; Layout.preferredHeight: 10
            radius: height / 2
            color: "#142219"
            border.width: 1; border.color: "#334331"
            Rectangle {
                id: meterFill; objectName: "meterFill"
                x: 1; y: 1
                width: meter.known ? (parent.width - 2) * Math.max(0, Math.min(1, meter.level)) : 0
                height: parent.height - 2
                radius: height / 2
                visible: meter.known
                gradient: Gradient {
                    GradientStop { position: 0; color: meter.accent }
                    GradientStop { position: 1; color: meter.accentDeep }
                }
                Rectangle {
                    objectName: "meterHighlight"
                    x: 2; y: 1
                    width: Math.max(0, parent.width - 4); height: 2
                    radius: 1; color: "#eef0d7"; opacity: 0.18
                    visible: parent.width > 6
                }
            }
            Rectangle {
                anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                anchors.leftMargin: 2; anchors.rightMargin: 2
                height: 2; radius: 1
                color: "#0c1610"; opacity: 0.28
            }
        }
    }

    // One still wash carries the habitat's light into the surrounding surface.
    Shape {
        anchors.fill: parent; preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: 0
            fillGradient: RadialGradient {
                centerX: home.width * 0.28; centerY: home.height * 0.35
                focalX: centerX; focalY: centerY
                centerRadius: Math.max(home.width, home.height) * 0.76
                GradientStop { position: 0; color: "#126d8058" }
                GradientStop { position: 0.6; color: "#065d7050" }
                GradientStop { position: 1; color: "#005d7050" }
            }
            startX: 0; startY: 0
            PathLine { x: home.width; y: 0 }
            PathLine { x: home.width; y: home.height }
            PathLine { x: 0; y: home.height }
            PathLine { x: 0; y: 0 }
        }
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: home.pageMargin
        spacing: 22

        // A restrained masthead; the repository reads as the habitat's address.
        RowLayout {
            Layout.fillWidth: true; spacing: 24
            ColumnLayout {
                spacing: 6
                Copy { text: bridge.name.toUpperCase(); font.pixelSize: 25; font.letterSpacing: 7 }
                Eyebrow { text: "A REPOSITORY HABITAT"; font.pixelSize: 8; font.letterSpacing: 1.8 }
            }
            Item { Layout.fillWidth: true }
            ColumnLayout {
                Layout.maximumWidth: home.wide ? 340 : 240
                Layout.fillWidth: true; spacing: 5
                Small { Layout.fillWidth: true; text: bridge.repoName; horizontalAlignment: Text.AlignRight; color: "#c4cbb3"; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                Small {
                    Layout.fillWidth: true; text: bridge.repoPath; font.pixelSize: 10; color: "#87947e"
                    horizontalAlignment: Text.AlignRight; elide: Text.ElideMiddle; wrapMode: Text.NoWrap
                    ToolTip.visible: repoHover.hovered; ToolTip.text: bridge.repoPath
                    HoverHandler { id: repoHover }
                }
            }
        }

        Flickable {
            id: page; objectName: "habitatScroll"
            Layout.fillWidth: true; Layout.fillHeight: true
            Layout.minimumHeight: 0; Layout.preferredHeight: 1
            contentWidth: width; contentHeight: regions.height; clip: true
            flickableDirection: Flickable.VerticalFlick
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { }
            Item {
                id: regions
                width: page.width
                height: home.wide ? Math.max(435, page.height) : home.compactGardenHeight + home.regionGap + 400

                // Only region geometry changes at the breakpoint. The same
                // creature, journal and bindings survive a resize.
                ColumnLayout {
                    id: garden; objectName: "gardenRegion"
                    width: home.wide ? (regions.width - home.regionGap) * 0.62 : regions.width
                    height: home.wide ? regions.height : home.compactGardenHeight
                    spacing: 10
                    Habitat {
                        id: habitat; objectName: "habitatScene"
                        bridge: home.bridge
                        Layout.fillWidth: true; Layout.fillHeight: true
                        Layout.minimumHeight: 310
                    }
                    Copy {
                        objectName: "moodLabel"; Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter; font.pixelSize: 13
                        text: bridge.ready ? bridge.mood + " · " + habitat.pose : ""
                        color: "#c2c9ab"
                    }
                    Small {
                        objectName: "wishLabel"; Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter; text: "Wish · " + bridge.wish
                        visible: bridge.wish.length > 0; font.italic: true
                    }
                    RowLayout {
                        objectName: "vitals"
                        Layout.fillWidth: true; Layout.topMargin: 15
                        Layout.leftMargin: 14; Layout.rightMargin: 14; spacing: 30
                        Meter {
                            id: hungerMeter; objectName: "hungerMeter"
                            Layout.fillWidth: true
                            caption: "Hunger"; level: bridge.hunger; known: bridge.ready
                            accent: "#aeb06c"; accentDeep: "#666a42"
                        }
                        Meter {
                            id: energyMeter; objectName: "energyMeter"
                            Layout.fillWidth: true
                            caption: "Energy"; level: bridge.energy; known: bridge.ready
                            accent: "#8eae77"; accentDeep: "#4d7654"
                        }
                    }
                }

                Item {
                    id: notes; objectName: "notesRegion"
                    x: home.wide ? garden.width + home.regionGap : 0
                    y: home.wide ? 0 : garden.height + home.regionGap
                    width: home.wide ? regions.width - x : regions.width
                    height: home.wide ? regions.height : 400

                    // A quiet archival page: tactile enough to belong to the habitat,
                    // restrained enough that Moss remains the dominant focal point.
                    Rectangle {
                        id: journalPage; objectName: "journalPage"
                        anchors.fill: parent; radius: 4
                        border.width: 1; border.color: "#24372b"
                        gradient: Gradient {
                            GradientStop { position: 0; color: "#c31e2c21" }
                            GradientStop { position: 0.52; color: "#721b291f" }
                            GradientStop { position: 1; color: "#1219251d" }
                        }
                    }
                    Rectangle {
                        x: 0; y: 28; width: 1; height: parent.height - 56
                        gradient: Gradient {
                            GradientStop { position: 0; color: "#003c4533" }
                            GradientStop { position: 0.12; color: "#804b563c" }
                            GradientStop { position: 0.65; color: "#403c4533" }
                            GradientStop { position: 1; color: "#003c4533" }
                        }
                    }
                    ScrollView {
                        id: journalScroll; objectName: "journalScroll"
                        anchors.fill: parent; anchors.margins: home.wide ? 26 : 22
                        contentWidth: availableWidth; clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        ColumnLayout {
                            id: journal
                            width: journalScroll.availableWidth
                            spacing: 0

                            RowLayout {
                                Layout.fillWidth: true; spacing: 12
                                Eyebrow { text: "FIELD NOTES"; color: "#b0b896" }
                                Rectangle {
                                    Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter
                                    height: 1; color: "#2e402f"; opacity: 0.8
                                }
                            }
                            Small {
                                Layout.topMargin: 7
                                text: "A small life, recorded."; color: "#8f9b86"; font.italic: true
                            }

                            ColumnLayout {
                                id: journalEntry; objectName: "journalEntry"
                                Layout.fillWidth: true; Layout.topMargin: 24
                                spacing: 12
                                Eyebrow {
                                    text: "LATEST OBSERVATION"
                                    font.pixelSize: 8; font.letterSpacing: 1.6; color: "#7f8e78"
                                }
                                Copy {
                                    id: latest; objectName: "latestDiary"
                                    Layout.fillWidth: true
                                    font.family: "Georgia"; font.pixelSize: home.wide ? 25 : 23
                                    lineHeight: 1.3; color: "#e4e1ca"
                                    text: bridge.diaryEntries.length ? bridge.diaryEntries[0] : (bridge.ready ? "The first page is still waiting." : "")
                                }
                            }

                            RowLayout {
                                id: journalAnnotation; objectName: "journalAnnotation"
                                Layout.fillWidth: true; Layout.topMargin: 19
                                visible: bridge.thought.length > 0
                                spacing: 12
                                Rectangle {
                                    Layout.preferredWidth: 2; Layout.preferredHeight: 34
                                    Layout.alignment: Qt.AlignTop
                                    radius: 1; color: "#58664c"; opacity: 0.65
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 5
                                    Eyebrow {
                                        text: "MARGIN NOTE"
                                        font.pixelSize: 7; font.letterSpacing: 1.5; color: "#75836f"
                                    }
                                    Small {
                                        objectName: "thoughtLabel"; Layout.fillWidth: true
                                        text: bridge.thought
                                        font.italic: true; lineHeight: 1.28; color: "#9daa92"
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true; Layout.topMargin: 22
                                height: 1; color: "#30412f"; opacity: 0.85
                            }
                            QuietButton {
                                objectName: "historyButton"; visible: bridge.diaryEntries.length > 1
                                Layout.leftMargin: -8; Layout.topMargin: 5
                                text: home.historyOpen ? "Close earlier field notes" : "Earlier field notes (" + (bridge.diaryEntries.length - 1) + ")"
                                onClicked: home.historyOpen = !home.historyOpen
                            }
                            ColumnLayout {
                                objectName: "diaryHistory"; Layout.fillWidth: true
                                Layout.topMargin: 8
                                visible: home.historyOpen && bridge.diaryEntries.length > 1; spacing: 22
                                Repeater {
                                    model: bridge.diaryEntries.slice(1)
                                    Copy {
                                        required property string modelData
                                        Layout.fillWidth: true; text: modelData
                                        font.family: "Georgia"; font.pixelSize: 14
                                        color: "#9fab91"; lineHeight: 1.4
                                    }
                                }
                            }

                            ColumnLayout {
                                id: journalArchiveMeta; objectName: "journalArchiveMeta"
                                Layout.fillWidth: true; Layout.topMargin: 22
                                spacing: 7
                                Rectangle {
                                    Layout.fillWidth: true; height: 1
                                    color: "#2a392b"; opacity: 0.75
                                }
                                Small {
                                    objectName: "lifetimeSummary"; Layout.fillWidth: true; visible: bridge.ready
                                    text: "Life here · " + bridge.commitsEaten + " commits eaten · " + bridge.sulks + " sulks · longest quiet spell " + bridge.longestNeglectDays + " days"
                                    font.pixelSize: 10; lineHeight: 1.35; color: "#84917c"
                                }
                                Small {
                                    objectName: "mealSummary"; Layout.fillWidth: true; visible: bridge.hasTick
                                    text: "Last tick · " + bridge.commitsArrived + " arrived in the bowl · " + bridge.commitsEatenThisTick + " eaten"
                                    font.pixelSize: 10; lineHeight: 1.3; color: "#8b9882"
                                }
                                Eyebrow {
                                    Layout.topMargin: 11
                                    text: "COMMITS ARE FOOD"
                                    font.pixelSize: 8; font.letterSpacing: 1.7; color: "#77866e"
                                }
                            }
                        }
                    }
                }
            }
        }

        // Persistent footer: working, fallback and failed-save states never
        // disappear into diary history. Opening details is presentation only.
        ColumnLayout {
            Layout.fillWidth: true; spacing: 10
            Rectangle { Layout.fillWidth: true; height: 1; color: "#34402e" }
            Copy {
                objectName: "errorLabel"; Layout.fillWidth: true
                visible: bridge.error.length > 0; text: bridge.error
                color: "#e2b592"; font.pixelSize: 12
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 18
                Rectangle {
                    Layout.alignment: Qt.AlignVCenter
                    width: 5; height: 5; radius: 3
                    color: bridge.error.length || bridge.usedFallback ? "#d4aa79" : "#9eaf7c"
                    opacity: bridge.busy ? 0.45 : 0.8
                    SequentialAnimation on opacity {
                        running: bridge.busy; loops: Animation.Infinite
                        NumberAnimation { to: 0.3; duration: 1200; easing.type: Easing.InOutSine }
                        NumberAnimation { to: 0.9; duration: 1200; easing.type: Easing.InOutSine }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 5
                    Small {
                        objectName: "brainSummary"; Layout.fillWidth: true
                        text: bridge.hasTick ? bridge.brainStatus : "Selected brain · " + bridge.brainLabel
                        color: bridge.usedFallback ? "#d4aa79" : "#b0bb9e"
                    }
                    Small { Layout.fillWidth: true; text: bridge.activity; font.pixelSize: 11 }
                }
                Button {
                    objectName: "tickButton"; Layout.preferredWidth: 120; Layout.preferredHeight: 42
                    text: bridge.busy ? "Working…" : bridge.ready ? "Live a tick" : "Open home"
                    font.pixelSize: 13
                    enabled: !bridge.busy && !bridge.closing
                    onClicked: bridge.ready ? bridge.requestTick() : bridge.open()
                    background: Rectangle { color: parent.down ? "#485b39" : parent.hovered ? "#3c5235" : "#30452e"; radius: 3; border.color: "#526045" }
                }
            }
            QuietButton {
                objectName: "detailsButton"; Layout.leftMargin: -8
                text: home.detailsOpen ? "Close habitat details" : "Habitat details"
                onClicked: home.detailsOpen = !home.detailsOpen
            }
            ScrollView {
                id: detailsScroll
                Layout.fillWidth: true; Layout.preferredHeight: Math.min(180, details.implicitHeight)
                visible: home.detailsOpen; contentWidth: availableWidth; clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ColumnLayout {
                    id: details; objectName: "habitatDetails"
                    width: detailsScroll.availableWidth; spacing: 9
                    Small { Layout.fillWidth: true; text: "Brain · " + bridge.brainLabel }
                    Small { Layout.fillWidth: true; text: "Last decision · " + bridge.brainStatus + (bridge.hasTick ? " · " + bridge.decisionAttempts + " attempts" : "") }
                    Small { Layout.fillWidth: true; text: "Git · " + bridge.repoStatus }
                    Small { Layout.fillWidth: true; text: "Last observed commit · " + (bridge.lastCommitAt || "Not available this visit"); wrapMode: Text.WrapAnywhere }
                    Small { Layout.fillWidth: true; visible: bridge.hasTick; text: "Scene at last tick · " + (bridge.isNight ? "night" : "day") + " (UTC) · " + bridge.hoursQuiet.toFixed(1) + " hours quiet" }
                    Small { Layout.fillWidth: true; visible: bridge.hasTick && !bridge.lastCommitAt; text: "Without a commit timestamp, quiet time is measured from the previous tick. Git sensing cannot distinguish empty history from failure." }
                    Small { Layout.fillWidth: true; text: "State as of · " + (bridge.lastTick || "—"); wrapMode: Text.WrapAnywhere }
                    Small { Layout.fillWidth: true; text: "Home file · " + bridge.statePath; wrapMode: Text.WrapAnywhere }
                    Small { Layout.fillWidth: true; text: "Use one Moss process per home. No background ticks." }
                }
            }
        }
    }
}