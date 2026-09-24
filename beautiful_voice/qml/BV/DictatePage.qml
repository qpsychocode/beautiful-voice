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
            title: page.t.dictate_title
            subtitle: page.t.dictate_subtitle
        }

        // The stage: a live copy of the pill on a blue-to-pink dusk.
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 300
            radius: 26
            clip: true
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: Theme.duskA }
                GradientStop { position: 1; color: Theme.duskB }
            }

            // Two soft glows keep the gradient from looking flat.
            Rectangle {
                width: 420; height: 420; radius: 210
                x: -120; y: -220
                color: Qt.rgba(1, 1, 1, Theme.dark ? 0.04 : 0.35)
            }
            Rectangle {
                width: 360; height: 360; radius: 180
                x: parent.width - 220; y: 140
                color: Qt.rgba(1, 1, 1, Theme.dark ? 0.03 : 0.28)
            }

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 26

                VoicePill {
                    Layout.alignment: Qt.AlignHCenter
                    u: 1.45
                    phase: backend.state === "idle" ? "idle" : backend.state
                    level: backend.level
                    message: backend.notice
                    doneText: page.t.pill_done
                    showStart: backend.state === "idle" && backend.activeModelId !== ""
                    onStartClicked: backend.toggleDictation()
                    onCloseClicked: backend.cancelDictation()
                }

                // With a model: how to use the hotkey. Without: where to get one.
                ColumnLayout {
                    Layout.alignment: Qt.AlignHCenter
                    visible: backend.activeModelId !== ""
                    spacing: 12
                    Row {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 12
                        Keycaps { keys: backend.hotkeyKeys; anchors.verticalCenter: parent.verticalCenter }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: backend.settings.hotkey_mode === "hold" ? page.t.hint_hold : page.t.hint_toggle
                            color: Theme.ink
                            font.family: Theme.body
                            font.pixelSize: 14
                        }
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: page.t.hint_escape
                        color: Theme.muted
                        font.family: Theme.body
                        font.pixelSize: 13
                    }
                }
                // First start: the default model is downloading.
                ColumnLayout {
                    Layout.alignment: Qt.AlignHCenter
                    visible: backend.activeModelId === "" && backend.firstDownload.id !== undefined
                    spacing: 10
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: page.t.first_download.replace("{name}", backend.firstDownload.name || "")
                                                   .replace("{progress}", backend.firstDownload.progressText || "")
                        color: Theme.ink
                        font.family: Theme.body
                        font.pixelSize: 14
                    }
                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        width: 320
                        height: 6
                        radius: 3
                        color: Qt.rgba(1, 1, 1, Theme.dark ? 0.12 : 0.6)
                        Rectangle {
                            height: parent.height
                            radius: 3
                            width: Math.max(height, parent.width * (backend.firstDownload.progress || 0))
                            Behavior on width { NumberAnimation { duration: 200 } }
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0; color: Theme.cornflower }
                                GradientStop { position: 1; color: Theme.blush }
                            }
                        }
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: page.t.first_download_hint
                        color: Theme.muted
                        font.family: Theme.body
                        font.pixelSize: 13
                    }
                }
                ColumnLayout {
                    Layout.alignment: Qt.AlignHCenter
                    visible: backend.activeModelId === "" && backend.firstDownload.id === undefined
                    spacing: 14
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: page.t.no_model_hint
                        color: Theme.ink
                        font.family: Theme.body
                        font.pixelSize: 14
                    }
                    ActionButton {
                        Layout.alignment: Qt.AlignHCenter
                        text: page.t.pick_model
                        icon: "models"
                        onClicked: page.navigate("models")
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 18

            // Active model
            Card {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                Layout.minimumHeight: 212
                ColumnLayout {
                    width: parent.width
                    spacing: 0
                    Text {
                        text: page.t.card_model
                        color: Theme.faint
                        font.family: Theme.bodyStrong
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.1
                    }
                    Text {
                        Layout.topMargin: 8
                        Layout.fillWidth: true
                        text: backend.activeModel.name || page.t.model_none
                        color: Theme.ink
                        font.family: Theme.bodyStrong
                        font.pixelSize: 19
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.topMargin: 4
                        text: backend.activeModel.statusText || page.t.model_none_hint
                        color: backend.modelStatus === "error" ? Theme.danger : Theme.muted
                        font.family: Theme.body
                        font.pixelSize: 13
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Meter {
                        Layout.topMargin: 18
                        Layout.fillWidth: true
                        visible: backend.activeModelId !== ""
                        label: page.t.metric_accuracy
                        value: backend.activeModel.accuracy >= 0 ? backend.activeModel.accuracy / 100 : -1
                        valueText: backend.activeModel.accuracyText || ""
                        color: Theme.accuracy
                    }
                    Meter {
                        Layout.topMargin: 6
                        Layout.fillWidth: true
                        visible: backend.activeModelId !== ""
                        label: page.t.metric_speed
                        value: backend.activeModel.speedValue || 0
                        valueText: backend.activeModel.speedText || ""
                        color: Theme.speed
                    }
                    ActionButton {
                        Layout.topMargin: 18
                        text: page.t.change_model
                        variant: "secondary"
                        compact: true
                        onClicked: page.navigate("models")
                    }
                }
            }

            // Last dictation
            Card {
                Layout.fillWidth: true
                Layout.preferredWidth: 1.25
                Layout.alignment: Qt.AlignTop
                Layout.minimumHeight: 212
                ColumnLayout {
                    width: parent.width
                    spacing: 0
                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            Layout.fillWidth: true
                            text: page.t.card_last
                            color: Theme.faint
                            font.family: Theme.bodyStrong
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                            font.letterSpacing: 1.1
                        }
                        IconButton {
                            visible: backend.lastText !== ""
                            icon: "copy"
                            tip: page.t.copy
                            onClicked: backend.copyText(backend.lastText)
                        }
                    }
                    Text {
                        Layout.topMargin: 6
                        Layout.fillWidth: true
                        text: backend.lastText !== "" ? backend.lastText : page.t.last_empty
                        color: backend.lastText !== "" ? Theme.ink : Theme.muted
                        font.family: Theme.body
                        font.pixelSize: backend.lastText !== "" ? 15 : 14
                        lineHeight: 1.4
                        wrapMode: Text.WordWrap
                        maximumLineCount: 5
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.topMargin: 12
                        visible: backend.lastMeta !== ""
                        text: backend.lastMeta
                        color: Theme.faint
                        font.family: Theme.numeric
                        font.pixelSize: 12
                    }
                }
            }
        }

        Text {
            Layout.fillWidth: true
            visible: backend.totalsText !== ""
            text: backend.totalsText
            color: Theme.muted
            font.family: Theme.display
            font.italic: Theme.italicTitles
            font.pixelSize: 17
            wrapMode: Text.WordWrap
        }
    }
}
