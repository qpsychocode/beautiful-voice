import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root
    property string title: ""
    property string subtitle: ""
    default property alias actions: actionRow.data
    spacing: 6

    RowLayout {
        Layout.fillWidth: true
        spacing: 12
        Text {
            Layout.fillWidth: true
            text: root.title
            color: Theme.ink
            font.family: Theme.display
            font.italic: Theme.italicTitles
            font.pixelSize: 38
            font.letterSpacing: -0.4
        }
        Row {
            id: actionRow
            spacing: 8
            Layout.alignment: Qt.AlignBottom
        }
    }
    Text {
        Layout.fillWidth: true
        Layout.maximumWidth: 700
        visible: root.subtitle !== ""
        text: root.subtitle
        color: Theme.muted
        font.family: Theme.body
        font.pixelSize: 14
        lineHeight: 1.15
        wrapMode: Text.WordWrap
    }
}
