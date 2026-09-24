import QtQuick
import QtQuick.Layouts

Flickable {
    id: page
    readonly property var t: i18n.t
    signal navigate(string page)

    contentHeight: col.implicitHeight + 80
    clip: true
    boundsBehavior: Flickable.StopAtBounds

    ColumnLayout {
        id: col
        x: 44
        y: 40
        width: Math.min(page.width - 88, 920)
        spacing: 22

        PageHeader {
            Layout.fillWidth: true
            title: page.t.history_title
            subtitle: backend.historySubtitle
            ActionButton {
                visible: historyModel.count > 0
                text: page.t.history_clear
                icon: "trash"
                variant: "danger"
                compact: true
                onClicked: confirm.visible = true
            }
        }

        // Clearing is permanent, so it asks once.
        Rectangle {
            id: confirm
            visible: false
            Layout.fillWidth: true
            radius: Theme.radiusSmall
            color: Theme.surfaceSunk
            border.width: 1
            border.color: Theme.lineStrong
            implicitHeight: 60
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 12
                spacing: 10
                Text {
                    Layout.fillWidth: true
                    text: page.t.history_clear_confirm
                    color: Theme.ink
                    font.family: Theme.body
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    text: page.t.cancel
                    variant: "ghost"
                    compact: true
                    onClicked: confirm.visible = false
                }
                ActionButton {
                    text: page.t.history_clear
                    compact: true
                    onClicked: { backend.clearHistory(); confirm.visible = false }
                }
            }
        }

        Repeater {
            model: historyModel
            delegate: Rectangle {
                id: entry
                required property var model
                Layout.fillWidth: true
                implicitHeight: body.implicitHeight + 34
                radius: Theme.radius
                color: Theme.surface
                border.width: 1
                border.color: hover.hovered ? Theme.lineStrong : Theme.line

                HoverHandler { id: hover }

                RowLayout {
                    id: body
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 17
                    anchors.leftMargin: 22
                    spacing: 22

                    ColumnLayout {
                        Layout.alignment: Qt.AlignTop
                        Layout.preferredWidth: 64
                        spacing: 2
                        Text {
                            text: entry.model.time
                            color: Theme.ink
                            font.family: Theme.numeric
                            font.pixelSize: 16
                        }
                        Text {
                            text: entry.model.day
                            color: Theme.faint
                            font.family: Theme.body
                            font.pixelSize: 12
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TextEdit {
                            Layout.fillWidth: true
                            text: entry.model.text
                            readOnly: true
                            selectByMouse: true
                            wrapMode: TextEdit.WordWrap
                            color: Theme.ink
                            selectionColor: Theme.cornflower
                            selectedTextColor: "#FFFFFF"
                            font.family: Theme.body
                            font.pixelSize: 15
                        }
                        Text {
                            text: entry.model.meta
                            color: Theme.faint
                            font.family: Theme.numeric
                            font.pixelSize: 12
                        }
                    }

                    Row {
                        Layout.alignment: Qt.AlignTop
                        spacing: 2
                        opacity: hover.hovered ? 1 : 0.35
                        Behavior on opacity { NumberAnimation { duration: 120 } }
                        IconButton {
                            icon: "copy"
                            tip: page.t.copy
                            onClicked: backend.copyText(entry.model.text)
                        }
                        IconButton {
                            icon: "trash"
                            tip: page.t.delete
                            onClicked: backend.deleteHistory(entry.model.id)
                        }
                    }
                }
            }
        }

        // Empty state
        Rectangle {
            visible: historyModel.count === 0
            Layout.fillWidth: true
            implicitHeight: empty.implicitHeight + 64
            radius: Theme.radius
            color: Theme.surfaceSunk
            border.width: 1
            border.color: Theme.line

            ColumnLayout {
                id: empty
                anchors.left: parent.left
                anchors.leftMargin: 32
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12
                LogoMark { s: 40 }
                Text {
                    Layout.topMargin: 4
                    text: page.t.history_empty_title
                    color: Theme.ink
                    font.family: Theme.display
                    font.italic: Theme.italicTitles
                    font.pixelSize: 24
                }
                Row {
                    spacing: 8
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: page.t.history_empty_hint
                        color: Theme.muted
                        font.family: Theme.body
                        font.pixelSize: 14
                    }
                    Keycaps { keys: backend.hotkeyKeys; small: true; anchors.verticalCenter: parent.verticalCenter }
                }
            }
        }
    }
}
