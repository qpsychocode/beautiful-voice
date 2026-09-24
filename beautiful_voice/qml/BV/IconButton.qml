import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    property string icon: "x"
    property string tip: ""
    property color tint: Theme.muted
    property real iconSize: 17
    signal clicked()

    implicitWidth: 32
    implicitHeight: 32
    radius: width / 2
    color: area.pressed ? Theme.track : area.containsMouse ? Theme.hover : "transparent"
    Behavior on color { ColorAnimation { duration: 110 } }

    Icon {
        anchors.centerIn: parent
        name: root.icon
        size: root.iconSize
        color: area.containsMouse ? Theme.ink : root.tint
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }

    ToolTip.visible: tip !== "" && area.containsMouse
    ToolTip.delay: 500
    ToolTip.text: tip
}
