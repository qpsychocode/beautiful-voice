import QtQuick

Rectangle {
    id: root
    property bool checked: false
    signal toggled(bool value)

    implicitWidth: 42
    implicitHeight: 24
    radius: height / 2
    color: checked ? "transparent" : Theme.track
    border.width: checked ? 0 : 1
    border.color: Theme.lineStrong

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        opacity: root.checked ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 160 } }
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: Theme.cornflower }
            GradientStop { position: 1; color: Theme.blush }
        }
    }

    Rectangle {
        width: 18
        height: 18
        radius: 9
        y: 3
        x: root.checked ? root.width - width - 3 : 3
        color: root.checked ? "#FFFFFF" : Theme.surface
        border.width: root.checked ? 0 : 1
        border.color: Theme.lineStrong
        Behavior on x { NumberAnimation { duration: 170; easing.type: Easing.OutCubic } }
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggled(!root.checked)
    }

    activeFocusOnTab: true
    Keys.onSpacePressed: root.toggled(!root.checked)
    Rectangle {
        visible: root.activeFocus
        anchors.fill: parent
        anchors.margins: -3
        radius: height / 2
        color: "transparent"
        border.width: 2
        border.color: Theme.cornflower
    }
}
