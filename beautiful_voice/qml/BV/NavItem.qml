import QtQuick

Rectangle {
    id: root
    property string text: ""
    property string icon: ""
    property bool selected: false
    property string badge: ""
    signal clicked()

    implicitHeight: 40
    radius: 12
    color: selected ? Theme.surface : area.containsMouse ? Qt.rgba(Theme.surface.r, Theme.surface.g, Theme.surface.b, 0.5) : "transparent"
    border.width: selected ? 1 : 0
    border.color: Theme.line
    Behavior on color { ColorAnimation { duration: 120 } }

    Icon {
        id: glyph
        anchors.left: parent.left
        anchors.leftMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        name: root.icon
        size: 19
        color: root.selected ? Theme.blueText : Theme.muted
    }

    Text {
        anchors.left: glyph.right
        anchors.leftMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        text: root.text
        color: root.selected ? Theme.ink : Theme.muted
        font.family: Theme.body
        font.pixelSize: 14
        font.weight: root.selected ? Font.DemiBold : Font.Normal
    }

    Rectangle {
        visible: root.badge !== ""
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        height: 18
        width: Math.max(18, badgeText.implicitWidth + 10)
        radius: 9
        color: Qt.rgba(Theme.blush.r, Theme.blush.g, Theme.blush.b, 0.28)
        Text {
            id: badgeText
            anchors.centerIn: parent
            text: root.badge
            color: Theme.pinkText
            font.family: Theme.numeric
            font.pixelSize: 11
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
