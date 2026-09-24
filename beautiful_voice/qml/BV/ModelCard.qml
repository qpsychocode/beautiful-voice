import QtQuick
import QtQuick.Layouts

Rectangle {
    id: card
    required property var row   // one entry of modelsModel, passed as a plain object
    readonly property var t: i18n.t

    radius: Theme.radius
    color: Theme.surface
    border.width: row.active ? 1.5 : 1
    border.color: row.active ? Theme.cornflower : Theme.line
    implicitHeight: body.implicitHeight + 44

    ColumnLayout {
        id: body
        anchors.fill: parent
        anchors.margins: 22
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Text {
                text: (card.row.vendor + " · " + card.row.family).toUpperCase()
                color: Theme.faint
                font.family: Theme.bodyStrong
                font.pixelSize: 11
                font.weight: Font.DemiBold
                font.letterSpacing: 1.1
            }
            Item { Layout.fillWidth: true }
            Tag {
                visible: card.row.active
                text: card.t.model_in_use
                tone: "ink"
            }
            Tag {
                visible: !card.row.active && card.row.recommended
                text: card.t.model_recommended
                tone: "pink"
            }
        }

        Text {
            Layout.topMargin: 8
            Layout.fillWidth: true
            text: card.row.name
            color: Theme.ink
            font.family: Theme.bodyStrong
            font.pixelSize: 19
            font.weight: Font.DemiBold
            elide: Text.ElideRight
        }

        Text {
            Layout.topMargin: 6
            Layout.fillWidth: true
            text: card.row.blurb
            color: Theme.muted
            font.family: Theme.body
            font.pixelSize: 13
            lineHeight: 1.3
            wrapMode: Text.WordWrap
            maximumLineCount: 3
            elide: Text.ElideRight
        }

        Text {
            Layout.topMargin: 8
            text: card.row.meta
            color: Theme.faint
            font.family: Theme.numeric
            font.pixelSize: 12
        }

        Meter {
            Layout.topMargin: 18
            Layout.fillWidth: true
            label: card.t.metric_accuracy
            value: card.row.accuracy >= 0 ? card.row.accuracy / 100 : -1
            valueText: card.row.accuracyText
            color: Theme.accuracy
        }
        Meter {
            Layout.topMargin: 6
            Layout.fillWidth: true
            label: card.t.metric_speed
            value: card.row.speedValue
            valueText: card.row.speedText
            color: Theme.speed
        }
        Text {
            Layout.topMargin: 8
            Layout.fillWidth: true
            text: card.row.source
            color: card.row.measured ? Theme.blueText : Theme.faint
            font.family: Theme.body
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }

        // Keeps the buttons of neighbouring cards on one line.
        Item { Layout.fillHeight: true }

        // Actions
        Item {
            Layout.topMargin: 18
            Layout.fillWidth: true
            implicitHeight: 38

            // Downloading
            RowLayout {
                anchors.fill: parent
                visible: card.row.downloading
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    Rectangle {
                        Layout.fillWidth: true
                        height: 6
                        radius: 3
                        color: Theme.track
                        Rectangle {
                            height: parent.height
                            radius: 3
                            width: Math.max(height, parent.width * card.row.progress)
                            Behavior on width { NumberAnimation { duration: 200 } }
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0; color: Theme.cornflower }
                                GradientStop { position: 1; color: Theme.blush }
                            }
                        }
                    }
                    Text {
                        text: card.row.progressText
                        color: Theme.muted
                        font.family: Theme.numeric
                        font.pixelSize: 12
                    }
                }
                ActionButton {
                    text: card.t.cancel
                    variant: "ghost"
                    compact: true
                    onClicked: backend.cancelDownload(card.row.id)
                }
            }

            // Not downloaded
            RowLayout {
                anchors.fill: parent
                visible: !card.row.downloading && !card.row.installed
                spacing: 10
                ActionButton {
                    text: card.t.download + " · " + card.row.sizeText
                    icon: "download"
                    onClicked: backend.downloadModel(card.row.id)
                }
                Text {
                    Layout.fillWidth: true
                    visible: card.row.error !== ""
                    text: card.row.error
                    color: Theme.danger
                    font.family: Theme.body
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }
            }

            // Installed
            RowLayout {
                anchors.fill: parent
                visible: !card.row.downloading && card.row.installed
                spacing: 10
                ActionButton {
                    visible: !card.row.active
                    text: card.t.model_use
                    variant: "secondary"
                    onClicked: backend.activateModel(card.row.id)
                }
                Row {
                    visible: card.row.active
                    spacing: 8
                    Icon {
                        anchors.verticalCenter: parent.verticalCenter
                        name: card.row.status === "error" ? "alert" : "check"
                        color: card.row.status === "error" ? Theme.danger : Theme.blueText
                        size: 17
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: card.row.statusText
                        color: card.row.status === "error" ? Theme.danger : Theme.ink
                        font.family: Theme.body
                        font.pixelSize: 13
                    }
                }
                Item { Layout.fillWidth: true }
                IconButton {
                    icon: "trash"
                    tip: card.t.model_delete
                    onClicked: backend.deleteModel(card.row.id)
                }
            }
        }
    }
}
