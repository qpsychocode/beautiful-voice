import QtQuick
import QtQuick.Controls

// options: [{value, label}]
ComboBox {
    id: root
    property var options: []
    property var current
    signal picked(var value)

    model: options
    textRole: "label"
    valueRole: "value"
    implicitWidth: 240
    implicitHeight: 36
    currentIndex: {
        for (let i = 0; i < options.length; ++i)
            if (options[i].value === current)
                return i
        return -1
    }
    onActivated: index => root.picked(options[index].value)
    font.family: Theme.body
    font.pixelSize: 13

    background: Rectangle {
        radius: Theme.radiusSmall
        color: root.hovered ? Theme.hover : Theme.surface
        border.width: 1
        border.color: root.activeFocus ? Theme.cornflower : Theme.lineStrong
    }

    contentItem: Text {
        leftPadding: 14
        rightPadding: 34
        text: root.currentIndex >= 0 ? root.options[root.currentIndex].label : ""
        color: Theme.ink
        font: root.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: Icon {
        x: root.width - width - 12
        y: (root.height - height) / 2
        name: "chevron"
        size: 16
        color: Theme.muted
    }

    delegate: ItemDelegate {
        required property var modelData
        required property int index
        width: root.popup.width - 8
        x: 4
        height: 34
        highlighted: root.highlightedIndex === index
        contentItem: Text {
            text: modelData.label
            color: Theme.ink
            font.family: Theme.body
            font.pixelSize: 13
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            leftPadding: 6
        }
        background: Rectangle {
            radius: 8
            color: parent.highlighted ? Theme.hover : "transparent"
        }
    }

    popup: Popup {
        y: root.height + 4
        width: root.width
        padding: 4
        implicitHeight: Math.min(contentItem.implicitHeight + 8, 320)
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }
        background: Rectangle {
            radius: Theme.radiusSmall
            color: Theme.surface
            border.width: 1
            border.color: Theme.line
        }
    }
}
