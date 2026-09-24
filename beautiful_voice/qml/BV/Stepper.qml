import QtQuick

// A number with − and + buttons; type a value directly into the middle.
Rectangle {
    id: root
    property int value: 10
    property int from: 1
    property int to: 1000
    property int step: 1
    signal valueEdited(int value)

    implicitWidth: 132
    implicitHeight: 36
    radius: height / 2
    color: Theme.surface
    border.width: 1
    border.color: input.activeFocus ? Theme.cornflower : Theme.lineStrong

    function commit(v) {
        v = Math.max(from, Math.min(to, v))
        if (v !== value)
            valueEdited(v)
    }

    Text {
        anchors.left: parent.left
        anchors.leftMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        width: 30; height: 30
        text: "−"
        color: root.value > root.from ? Theme.ink : Theme.faint
        font.pixelSize: 18
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: root.commit(root.value - root.step)
        }
    }

    TextInput {
        id: input
        anchors.centerIn: parent
        width: 56
        horizontalAlignment: Text.AlignHCenter
        text: root.value
        color: Theme.ink
        font.family: Theme.numeric
        font.pixelSize: 15
        validator: IntValidator { bottom: root.from; top: root.to }
        selectByMouse: true
        onEditingFinished: root.commit(parseInt(text) || root.from)
    }

    Text {
        anchors.right: parent.right
        anchors.rightMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        width: 30; height: 30
        text: "+"
        color: root.value < root.to ? Theme.ink : Theme.faint
        font.pixelSize: 18
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: root.commit(root.value + root.step)
        }
    }
}
