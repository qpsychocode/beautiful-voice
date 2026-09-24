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
    width: 600
    height: 110
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
