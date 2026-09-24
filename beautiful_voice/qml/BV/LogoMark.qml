import QtQuick

// The app mark: a black pill-shaped tile with five blue-to-pink bars.
Rectangle {
    id: root
    property real s: 34
    width: s
    height: s
    radius: s * 0.3
    color: Theme.onyx
    border.width: Theme.dark ? 1 : 0
    border.color: Theme.onyxLine

    Row {
        anchors.centerIn: parent
        spacing: root.s * 0.07
        Repeater {
            model: [0.34, 0.62, 0.9, 0.56, 0.3]
            Rectangle {
                required property var modelData
                required property int index
                width: root.s * 0.085
                height: root.s * 0.62 * modelData
                radius: width / 2
                anchors.verticalCenter: parent.verticalCenter
                color: Theme.mix(Theme.cornflower, Theme.blush, index / 4)
            }
        }
    }
}
