import QtQuick
import QtQuick.Layouts

Flickable {
    id: page
    readonly property var t: i18n.t

    contentHeight: col.implicitHeight + 80
    clip: true
    boundsBehavior: Flickable.StopAtBounds

    component StepTitle: RowLayout {
        id: step
        property string number: ""
        property string text: ""
        spacing: 12
        Rectangle {
            width: 26; height: 26; radius: 13
            color: Theme.primary
            Text {
                anchors.centerIn: parent
                text: step.number
                color: Theme.primaryInk
                font.family: Theme.numeric
                font.pixelSize: 13
            }
        }
        Text {
            text: step.text
            color: Theme.ink
            font.family: Theme.bodyStrong
            font.pixelSize: 17
            font.weight: Font.DemiBold
        }
    }

    ColumnLayout {
        id: col
        x: 44
        y: 40
        width: Math.min(page.width - 88, 920)
        spacing: 22

        PageHeader {
            Layout.fillWidth: true
            title: page.t.bench_title
            subtitle: page.t.bench_subtitle
        }

        Card {
            Layout.fillWidth: true
            ColumnLayout {
                width: parent.width
                spacing: 16

                RowLayout {
                    Layout.fillWidth: true
                    StepTitle { number: "1"; text: page.t.bench_step_read }
                    Item { Layout.fillWidth: true }
                    Dropdown {
                        width: 180
                        options: backend.benchLanguages
                        current: backend.benchLanguage
                        onPicked: v => backend.benchSetLanguage(v)
                    }
                    IconButton {
                        icon: "refresh"
                        tip: page.t.bench_other_text
                        onClicked: backend.benchNextPhrase()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    radius: Theme.radiusSmall
                    color: Theme.surfaceSunk
                    border.width: 1
                    border.color: Theme.line
                    implicitHeight: phrase.implicitHeight + 40
                    Text {
                        id: phrase
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.margins: 22
                        text: backend.benchPhrase
                        color: Theme.ink
                        font.family: Theme.body
                        font.pixelSize: 18
                        lineHeight: 1.3
                        wrapMode: Text.WordWrap
                    }
                }

                RowLayout {
                    spacing: 14
                    VoicePill {
                        visible: backend.benchState === "recording"
                        phase: "recording"
                        level: backend.benchLevel
                        showClose: false
                    }
                    ActionButton {
                        visible: backend.benchState !== "recording"
                        enabled: backend.benchState !== "running"
                        text: backend.benchSeconds > 0 ? page.t.bench_rerecord : page.t.bench_record
                        icon: "mic"
                        variant: backend.benchSeconds > 0 ? "secondary" : "primary"
                        onClicked: backend.benchRecordToggle()
                    }
                    ActionButton {
                        visible: backend.benchState === "recording"
                        text: page.t.bench_stop
                        icon: "stop"
                        onClicked: backend.benchRecordToggle()
                    }
                    Text {
                        Layout.fillWidth: true
                        text: backend.benchState === "recording" ? page.t.bench_recording_hint : backend.benchSampleText
                        color: Theme.muted
                        font.family: Theme.body
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        Card {
            Layout.fillWidth: true
            ColumnLayout {
                width: parent.width
                spacing: 16

                RowLayout {
                    Layout.fillWidth: true
                    StepTitle { number: "2"; text: page.t.bench_step_compare }
                    Item { Layout.fillWidth: true }
                    ActionButton {
                        visible: backend.benchState !== "running"
                        enabled: backend.benchSeconds > 0 && backend.installedCount > 0 && backend.benchState !== "recording"
                        text: page.t.bench_run
                        icon: "gauge"
                        onClicked: backend.benchRun()
                    }
                    ActionButton {
                        visible: backend.benchState === "running"
                        text: page.t.bench_cancel
                        variant: "secondary"
                        onClicked: backend.benchCancel()
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: backend.benchStatus
                    visible: text !== ""
                    color: Theme.muted
                    font.family: Theme.body
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }

                Repeater {
                    model: benchModel
                    delegate: Rectangle {
                        required property var model
                        Layout.fillWidth: true
                        implicitHeight: result.implicitHeight + 30
                        radius: Theme.radiusSmall
                        color: model.status === "running" ? Theme.hover : "transparent"
                        border.width: 1
                        border.color: Theme.line

                        ColumnLayout {
                            id: result
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.margins: 16
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Text {
                                    text: model.name
                                    color: Theme.ink
                                    font.family: Theme.bodyStrong
                                    font.pixelSize: 15
                                    font.weight: Font.DemiBold
                                }
                                Tag {
                                    visible: model.best !== ""
                                    text: model.best
                                    tone: model.bestTone
                                }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: model.statusText
                                    color: model.status === "error" ? Theme.danger : Theme.muted
                                    font.family: Theme.body
                                    font.pixelSize: 13
                                }
                            }
                            GridLayout {
                                Layout.fillWidth: true
                                columns: col.width > 700 ? 2 : 1
                                columnSpacing: 28
                                rowSpacing: 6
                                visible: model.status === "done"
                                Meter {
                                    Layout.fillWidth: true
                                    label: page.t.metric_accuracy
                                    value: model.accuracy / 100
                                    valueText: model.accuracyText
                                    color: Theme.accuracy
                                }
                                Meter {
                                    Layout.fillWidth: true
                                    label: page.t.metric_speed
                                    value: model.speedValue
                                    valueText: model.speedText
                                    color: Theme.speed
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                visible: model.hypothesis !== ""
                                text: "«" + model.hypothesis + "»"
                                color: Theme.muted
                                font.family: Theme.display
                                font.italic: Theme.italicTitles
                                font.pixelSize: 14
                                lineHeight: 1.35
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: benchModel.count === 0
                    text: backend.installedCount === 0 ? page.t.bench_need_models : page.t.bench_empty
                    color: Theme.muted
                    font.family: Theme.body
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
