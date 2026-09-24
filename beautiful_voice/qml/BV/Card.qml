import QtQuick

Rectangle {
    id: root
    default property alias content: inner.data
    property int padding: 22
    color: Theme.surface
    radius: Theme.radius
    border.width: 1
    border.color: Theme.line
    implicitHeight: inner.childrenRect.height + 2 * padding

    Item {
        id: inner
        anchors.fill: parent
        anchors.margins: root.padding
    }
}
