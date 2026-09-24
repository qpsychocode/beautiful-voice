import QtQuick
import QtQuick.Layouts

// Label and hint on the left, the control on the right.
Item {
    id: root
    property string label: ""
    property string hint: ""
    property bool last: false
    default property alias control: slot.data
    Layout.fillWidth: true
    implicitHeight: Math.max(texts.implicitHeight, slot.childrenRect.height) + 30

    ColumnLayout {
        id: texts
        anchors.left: parent.left
        anchors.right: slot.left
        anchors.rightMargin: 24
        anchors.verticalCenter: parent.verticalCenter
        spacing: 3
        Text {
            Layout.fillWidth: true
            text: root.label
            color: Theme.ink
            font.family: Theme.body
            font.pixelSize: 14
            font.weight: Font.DemiBold
            wrapMode: Text.WordWrap
        }
        Text {
            Layout.fillWidth: true
            visible: root.hint !== ""
            text: root.hint
            color: Theme.muted
            font.family: Theme.body
            font.pixelSize: 13
            lineHeight: 1.3
            wrapMode: Text.WordWrap
        }
    }

    Item {
        id: slot
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        width: childrenRect.width
        height: childrenRect.height
    }

    Rectangle {
        visible: !root.last
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: Theme.line
    }
}
