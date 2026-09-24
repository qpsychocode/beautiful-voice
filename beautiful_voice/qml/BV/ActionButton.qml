import QtQuick

// Primary actions borrow the black pill; everything else stays quiet.
Rectangle {
    id: root
    property string text: ""
    property string icon: ""
    property string variant: "primary"   // primary | secondary | ghost | danger
    property bool compact: false
    signal clicked()

    readonly property bool primary: variant === "primary"
    readonly property color fg: !enabled ? Theme.faint
                              : primary ? Theme.primaryInk
                              : variant === "danger" ? Theme.danger
                              : Theme.ink

    implicitHeight: compact ? 32 : 38
    implicitWidth: row.implicitWidth + (compact ? 26 : 34)
    radius: height / 2
    color: {
        if (primary)
            return !enabled ? Theme.track : area.pressed ? Theme.primaryPressed : area.containsMouse ? Theme.primaryHover : Theme.primary
        if (variant === "secondary")
            return area.pressed ? Theme.track : area.containsMouse ? Theme.hover : Theme.surface
        return area.containsMouse && enabled ? Theme.hover : "transparent"
    }
    border.width: variant === "secondary" ? 1 : 0
    border.color: Theme.lineStrong
    Behavior on color { ColorAnimation { duration: 110 } }

    Rectangle {
        // Soft blue-pink rim on the primary pill while hovered.
        visible: root.primary && root.enabled
        anchors.fill: parent
        anchors.margins: -1.5
        radius: height / 2
        z: -1
        opacity: area.containsMouse ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 160 } }
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: Theme.cornflower }
            GradientStop { position: 1; color: Theme.blush }
        }
    }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 8
        Icon {
            visible: root.icon !== ""
            anchors.verticalCenter: parent.verticalCenter
            name: root.icon
            color: root.primary && root.enabled ? Theme.primaryAccent : root.fg
            size: root.compact ? 15 : 17
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.text
            color: root.fg
            font.family: Theme.bodyStrong
            font.pixelSize: root.compact ? 13 : 14
            font.weight: Font.DemiBold
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabled
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }

    activeFocusOnTab: true
    Keys.onReturnPressed: root.clicked()
    Keys.onSpacePressed: root.clicked()
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
