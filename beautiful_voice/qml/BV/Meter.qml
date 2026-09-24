import QtQuick
import QtQuick.Layouts

// One labelled bar: blue for accuracy, pink for speed. Text stays in ink;
// the colour only marks which measure the bar is.
Item {
    id: root
    property string label: ""
    property real value: 0          // 0..1
    property string valueText: ""
    property color color: Theme.accuracy
    property bool known: value >= 0
    property int labelWidth: 74
    property int valueWidth: 92
    implicitHeight: 22
    implicitWidth: 260

    RowLayout {
        anchors.fill: parent
        spacing: 10

        Text {
            Layout.preferredWidth: root.labelWidth
            text: root.label
            color: Theme.muted
            font.family: Theme.body
            font.pixelSize: 12
            elide: Text.ElideRight
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            height: 6
            radius: 3
            color: Theme.track

            Rectangle {
                height: parent.height
                radius: 3
                color: root.color
                width: root.known ? Math.max(height, parent.width * Math.min(1, root.value)) : 0
                Behavior on width { NumberAnimation { duration: 420; easing.type: Easing.OutCubic } }
            }
        }

        Text {
            Layout.preferredWidth: root.valueWidth
            horizontalAlignment: Text.AlignRight
            text: root.known ? root.valueText : "—"
            color: root.known ? Theme.ink : Theme.faint
            font.family: Theme.numeric
            font.pixelSize: 13
        }
    }
}
