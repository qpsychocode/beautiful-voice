import QtQuick

// A hotkey drawn as physical keys: ["Ctrl", "Shift", "Space"].
Row {
    id: root
    property var keys: []
    property bool small: false
    property bool onDark: false
    spacing: small ? 4 : 6

    Repeater {
        model: root.keys
        Rectangle {
            required property var modelData
            height: root.small ? 22 : 28
            width: Math.max(height, label.implicitWidth + (root.small ? 12 : 18))
            radius: root.small ? 6 : 8
            color: root.onDark ? Theme.onyxRaised : Theme.surface
            border.width: 1
            border.color: root.onDark ? Theme.onyxLine : Theme.lineStrong

            // A slightly deeper bottom edge makes it read as a key.
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 1
                height: 2
                radius: 1
                color: root.onDark ? "#0A0A12" : Theme.line
            }

            Text {
                id: label
                anchors.centerIn: parent
                anchors.verticalCenterOffset: -1
                text: modelData
                color: root.onDark ? "#E8E7F4" : Theme.ink
                font.family: Theme.numeric
                font.pixelSize: root.small ? 11 : 13
            }
        }
    }
}
