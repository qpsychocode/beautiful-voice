import QtQuick

Rectangle {
    id: root
    property string text: ""
    property string tone: "neutral"   // neutral | blue | pink | ink
    implicitHeight: 22
    implicitWidth: label.implicitWidth + 16
    radius: height / 2
    color: tone === "blue" ? Qt.rgba(Theme.cornflower.r, Theme.cornflower.g, Theme.cornflower.b, 0.16)
         : tone === "pink" ? Qt.rgba(Theme.blush.r, Theme.blush.g, Theme.blush.b, 0.22)
         : tone === "ink" ? Theme.primary
         : Theme.track

    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: root.tone === "blue" ? Theme.blueText
             : root.tone === "pink" ? Theme.pinkText
             : root.tone === "ink" ? Theme.primaryInk
             : Theme.muted
        font.family: Theme.bodyStrong
        font.pixelSize: 11
        font.weight: Font.DemiBold
        font.letterSpacing: 0.3
    }
}
