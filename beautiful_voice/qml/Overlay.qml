import QtQuick
import QtQuick.Window
import QtQuick.Effects
import BV

// The pill that floats at the bottom of the screen while you dictate.
// It never takes focus, so the text lands in the app you were typing in.
Window {
    id: overlay
    objectName: "overlay"
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus | Qt.NoDropShadowWindowHint
    color: "transparent"
    width: 640
    height: 170
    visible: false

    readonly property bool wanted: backend.state !== "idle"
    property string phase: "recording"

    onWantedChanged: {
        if (wanted) {
            hideTimer.stop()
            backend.placeOverlay()
            visible = true
        } else {
            hideTimer.restart()
        }
    }

    Connections {
        target: backend
        function onStateChanged() {
            if (backend.state === "recording")
                pill.tenths = 0  // a new recording may follow a cancelled one without a phase change
            if (backend.state !== "idle")
                overlay.phase = backend.state
        }
    }

    Timer {
        id: hideTimer
        interval: 280
        onTriggered: if (!overlay.wanted) overlay.visible = false
    }

    // What the model has understood so far, newest words on the right.
    Rectangle {
        id: caption
        readonly property bool shown: overlay.wanted && backend.settings.live_caption && backend.liveText !== ""
                                      && (overlay.phase === "recording" || overlay.phase === "processing")
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: pill.top
        anchors.bottomMargin: 10
        width: Math.min(captionText.implicitWidth + 32, overlay.width - 40)
        height: 38
        radius: 14
        color: Qt.rgba(0.063, 0.063, 0.098, 0.9)
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.08)
        opacity: shown ? 1 : 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 180 } }

        Text {
            id: captionText
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            text: backend.liveText
            color: "#F2F1FB"
            font.family: Theme.body
            font.pixelSize: 14
            elide: Text.ElideLeft
            horizontalAlignment: implicitWidth > width ? Text.AlignRight : Text.AlignHCenter
        }
    }

    VoicePill {
        id: pill
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: overlay.wanted ? 22 : 8
        Behavior on anchors.bottomMargin { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
        opacity: overlay.wanted ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 200 } }
        scale: overlay.wanted ? 1 : 0.94
        Behavior on scale { NumberAnimation { duration: 240; easing.type: Easing.OutBack } }

        phase: overlay.phase
        level: backend.level
        message: backend.notice
        doneText: i18n.t.pill_done
        onCloseClicked: backend.cancelDictation()

        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: "#70000010"
            shadowBlur: 0.9
            shadowVerticalOffset: 6
        }
    }
}
