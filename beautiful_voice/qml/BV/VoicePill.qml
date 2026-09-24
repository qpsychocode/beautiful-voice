import QtQuick

// The black pill: voice bars, a timer and a close button. The same component
// floats over other apps while recording and sits on the home screen.
Rectangle {
    id: pill

    property string phase: "idle"   // idle | recording | processing | done | message
    property real level: 0
    property string message: ""
    property string doneText: ""
    property bool showStart: false  // the home-screen copy offers a mic button when idle
    property bool showClose: true
    property real u: 1              // size multiplier
    signal closeClicked()
    signal startClicked()

    readonly property bool busy: phase === "recording" || phase === "processing"
    property int tenths: 0

    height: 44 * u
    radius: height / 2
    color: Theme.onyx
    border.width: 1
    border.color: Qt.rgba(1, 1, 1, 0.07)
    implicitWidth: content.implicitWidth + 2 * (phase === "message" || phase === "done" ? 18 : 10) * u
    width: implicitWidth
    Behavior on width { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }

    onPhaseChanged: if (phase === "recording") tenths = 0

    Timer {
        running: pill.phase === "recording"
        interval: 100
        repeat: true
        onTriggered: pill.tenths += 1
    }

    function clock(t) {
        const s = Math.floor(t / 10)
        const m = Math.floor(s / 60)
        return m + ":" + (s % 60 < 10 ? "0" : "") + (s % 60)
    }

    Row {
        id: content
        anchors.centerIn: parent
        spacing: 10 * pill.u

        Item {
            // Left breathing room that matches the round button on the right.
            width: 6 * pill.u
            height: 1
            visible: pill.phase !== "message" && pill.phase !== "done"
        }

        Rectangle {
            // Recording dot, only when there is no close button to show the state.
            visible: pill.phase === "recording" && !pill.showClose
            anchors.verticalCenter: parent.verticalCenter
            width: 8 * pill.u
            height: width
            radius: width / 2
            color: Theme.blush
            SequentialAnimation on opacity {
                running: pill.phase === "recording"
                loops: Animation.Infinite
                NumberAnimation { to: 0.35; duration: 600 }
                NumberAnimation { to: 1; duration: 600 }
            }
        }

        Icon {
            visible: pill.phase === "message"
            anchors.verticalCenter: parent.verticalCenter
            name: "alert"
            color: Theme.blush
            size: 18 * pill.u
        }

        Icon {
            visible: pill.phase === "done"
            anchors.verticalCenter: parent.verticalCenter
            name: "check"
            color: Theme.blush
            size: 18 * pill.u
            stroke: 2.2
        }

        Text {
            visible: pill.phase === "message" || pill.phase === "done"
            anchors.verticalCenter: parent.verticalCenter
            text: pill.phase === "done" ? pill.doneText : pill.message
            color: "#F2F1FB"
            font.family: Theme.body
            font.pixelSize: 13 * pill.u
            elide: Text.ElideRight
            width: Math.min(implicitWidth, 420 * pill.u)
        }

        VoiceBars {
            visible: pill.phase !== "message" && pill.phase !== "done"
            anchors.verticalCenter: parent.verticalCenter
            height: 22 * pill.u
            bars: 21
            barWidth: 3 * pill.u
            gap: 2.6 * pill.u
            minHeight: 3 * pill.u
            level: pill.level
            mode: pill.phase === "recording" ? "live" : pill.phase === "processing" ? "wave" : "idle"
        }

        Text {
            visible: pill.busy
            anchors.verticalCenter: parent.verticalCenter
            text: pill.clock(pill.tenths)
            color: pill.phase === "processing" ? "#8E8EA8" : "#F2F1FB"
            font.family: Theme.numeric
            font.pixelSize: 14 * pill.u
            horizontalAlignment: Text.AlignRight
            width: 34 * pill.u
        }

        Rectangle {
            id: button
            visible: (pill.busy && pill.showClose) || (!pill.busy && pill.showStart)
            anchors.verticalCenter: parent.verticalCenter
            width: 28 * pill.u
            height: width
            radius: width / 2
            color: hit.containsMouse ? "#34344A" : Theme.onyxRaised
            Behavior on color { ColorAnimation { duration: 120 } }

            Icon {
                anchors.centerIn: parent
                name: pill.busy ? "x" : "mic"
                color: pill.busy ? "#D9D8EA" : Theme.blush
                size: (pill.busy ? 14 : 16) * pill.u
                stroke: pill.busy ? 2 : 1.8
            }

            MouseArea {
                id: hit
                anchors.fill: parent
                anchors.margins: -4
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: pill.busy ? pill.closeClicked() : pill.startClicked()
            }
        }
    }
}
