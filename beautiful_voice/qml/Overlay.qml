import QtQuick
import QtQuick.Controls
import QtQuick.Window
import QtQuick.Effects
import BV

// The pill that floats at the bottom of the screen while you dictate, and the
// small mic button that waits there the rest of the time. The window never
// takes focus on its own, so the text lands in the app you were typing in;
// it only borrows the keyboard while you edit the live text by hand.
Window {
    id: overlay
    objectName: "overlay"
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus | Qt.NoDropShadowWindowHint
    color: "transparent"
    width: 640
    height: 300
    visible: false

    property bool armed: false  // set by the app once the window can no longer steal focus
    readonly property bool wanted: backend.state !== "idle"
    readonly property bool buttonShown: armed && !wanted && backend.settings.floating_button && !backend.fullscreenApp
    readonly property bool needed: armed && (wanted || buttonShown)
    property string phase: "recording"
    property bool editing: false

    onNeededChanged: {
        if (needed) {
            hideTimer.stop()
            if (!visible)
                backend.placeOverlay()
            visible = true
        } else {
            hideTimer.restart()
        }
    }
    onWantedChanged: if (wanted) backend.placeOverlay()

    function stopEditing() {
        if (editing) {
            editing = false
            backend.setOverlayEditing(false)
        }
    }

    Connections {
        target: backend
        function onStateChanged() {
            if (backend.state === "recording") {
                pill.tenths = 0  // a new recording may follow a cancelled one without a phase change
                caption.sync(true)
            } else {
                overlay.stopEditing()
            }
            if (backend.state !== "idle")
                overlay.phase = backend.state
        }
        function onLiveTextChanged() { caption.sync(false) }
    }

    Timer {
        id: hideTimer
        interval: 280
        onTriggered: if (!overlay.needed) overlay.visible = false
    }

    // Only the visible shapes catch the mouse; clicks anywhere else reach the windows below.
    Timer {
        running: overlay.visible
        interval: 60
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            const rects = []
            for (const item of [floatButton, caption, pill]) {
                if (!item.visible || item.opacity < 0.05)
                    continue
                const p = item.mapToItem(null, 0, 0)
                const pad = 12  // room for the shadow
                rects.push({ x: p.x - pad, y: p.y - pad, width: item.width + 2 * pad, height: item.height + 2 * pad })
            }
            backend.setOverlayMask(rects)
        }
    }

    // What the model has understood so far. Click it to fix a word or type your own;
    // what you change is what gets inserted, and new words keep arriving at the end.
    Rectangle {
        id: caption
        readonly property bool shown: overlay.wanted && backend.settings.live_caption
                                      && (overlay.phase === "recording"
                                          || (overlay.phase === "processing" && editor.text !== ""))
        property bool syncing: false

        function sync(reset) {
            if (editor.text === backend.liveText)
                return
            syncing = true
            const pos = editor.cursorPosition
            const atEnd = reset || pos >= editor.length
            editor.text = backend.liveText
            editor.cursorPosition = atEnd ? editor.length : Math.min(pos, editor.length)
            syncing = false
            if (!overlay.editing)
                flick.contentY = Math.max(0, flick.contentHeight - flick.height)
        }

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: pill.top
        anchors.bottomMargin: 10
        width: overlay.width - 60
        height: Math.min(Math.max(editor.implicitHeight, 40), 132) + 8
        radius: 14
        color: Qt.rgba(0.063, 0.063, 0.098, 0.94)
        border.width: 1
        border.color: overlay.editing ? Qt.rgba(0.96, 0.65, 0.78, 0.55) : Qt.rgba(1, 1, 1, 0.08)
        opacity: shown ? 1 : 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 180 } }

        Flickable {
            id: flick
            anchors.fill: parent
            anchors.topMargin: 4
            anchors.bottomMargin: 4
            anchors.rightMargin: 40
            clip: true
            contentWidth: width
            contentHeight: editor.implicitHeight
            boundsBehavior: Flickable.StopAtBounds

            TextArea.flickable: TextArea {
                id: editor
                readOnly: overlay.phase !== "recording"
                wrapMode: TextEdit.Wrap
                color: "#F2F1FB"
                selectionColor: Qt.rgba(0.96, 0.65, 0.78, 0.45)
                selectedTextColor: "#FFFFFF"
                placeholderText: i18n.t.overlay_placeholder
                placeholderTextColor: "#7E7E98"
                font.family: Theme.body
                font.pixelSize: 14
                leftPadding: 16
                rightPadding: 4
                topPadding: 8
                bottomPadding: 8
                background: null

                onTextChanged: if (!caption.syncing && overlay.editing) backend.editLiveText(text)

                Keys.onPressed: event => {
                    if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter)
                            && !(event.modifiers & Qt.ShiftModifier)) {
                        event.accepted = true
                        backend.toggleDictation()  // finish and insert
                    } else if (event.key === Qt.Key_Escape) {
                        event.accepted = true
                        backend.cancelDictation()
                    }
                }

                // The window doesn't take the keyboard by itself: a click asks for it.
                TapHandler {
                    enabled: !overlay.editing && !editor.readOnly
                    onTapped: eventPoint => {
                        overlay.editing = true
                        backend.setOverlayEditing(true)
                        editor.forceActiveFocus()
                        editor.cursorPosition = editor.positionAt(eventPoint.position.x, eventPoint.position.y)
                    }
                }
            }
        }

        // Wipe what's there and keep talking.
        Rectangle {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 7
            width: 28
            height: 28
            radius: 14
            visible: editor.text !== "" && !editor.readOnly
            color: clearHit.containsMouse ? "#34344A" : "transparent"
            Behavior on color { ColorAnimation { duration: 120 } }

            Icon {
                anchors.centerIn: parent
                name: "trash"
                color: "#B9B8CF"
                size: 15
                stroke: 1.8
            }

            MouseArea {
                id: clearHit
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    backend.editLiveText("")
                    caption.syncing = true
                    editor.text = ""
                    caption.syncing = false
                }
            }
        }
    }

    VoicePill {
        id: pill
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: overlay.wanted ? 22 : 8
        Behavior on anchors.bottomMargin { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
        opacity: overlay.wanted ? 1 : 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 200 } }
        scale: overlay.wanted ? 1 : 0.94
        Behavior on scale { NumberAnimation { duration: 240; easing.type: Easing.OutBack } }

        phase: overlay.phase
        level: backend.level
        message: backend.notice
        doneText: i18n.t.pill_done
        showStop: true
        onStopClicked: backend.toggleDictation()
        onCloseClicked: backend.cancelDictation()

        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: "#70000010"
            shadowBlur: 0.9
            shadowVerticalOffset: 6
        }
    }

    // Always within reach: click to start dictating into the app you're in.
    Rectangle {
        id: floatButton
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
        width: 40
        height: 40
        radius: 20
        color: floatHit.pressed ? "#26263A" : floatHit.containsMouse ? "#20202E" : Theme.onyx
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.09)
        opacity: overlay.buttonShown ? (floatHit.containsMouse ? 1 : 0.88) : 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 180 } }
        scale: floatHit.pressed ? 0.94 : 1
        Behavior on scale { NumberAnimation { duration: 90 } }

        Icon {
            anchors.centerIn: parent
            name: "mic"
            color: Theme.blush
            size: 19
            stroke: 1.9
        }

        MouseArea {
            id: floatHit
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            enabled: overlay.buttonShown
            onClicked: backend.toggleDictation()
        }

        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: "#60000010"
            shadowBlur: 0.7
            shadowVerticalOffset: 3
        }
    }
}
