import QtQuick

// A row of mutually exclusive choices. options: [{value, label}]
Rectangle {
    id: root
    property var options: []
    property var current
    signal picked(var value)

    implicitHeight: 34
    implicitWidth: row.implicitWidth + 6
    radius: height / 2
    color: Theme.track

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 2
        Repeater {
            model: root.options
            Rectangle {
                required property var modelData
                readonly property bool selected: modelData.value === root.current
                height: root.height - 6
                width: label.implicitWidth + 26
                radius: height / 2
                color: selected ? Theme.surface : area.containsMouse ? Theme.hover : "transparent"
                border.width: selected ? 1 : 0
                border.color: Theme.line
                Behavior on color { ColorAnimation { duration: 110 } }

                Text {
                    id: label
                    anchors.centerIn: parent
                    text: modelData.label
                    color: parent.selected ? Theme.ink : Theme.muted
                    font.family: Theme.body
                    font.pixelSize: 13
                    font.weight: parent.selected ? Font.DemiBold : Font.Normal
                }
                MouseArea {
                    id: area
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.picked(parent.modelData.value)
                }
            }
        }
    }
}
