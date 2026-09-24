import QtQuick
import QtQuick.Layouts

Flickable {
    id: page
    readonly property var t: i18n.t
    property string filter: "all"

    contentHeight: col.implicitHeight + 80
    clip: true
    boundsBehavior: Flickable.StopAtBounds

    function matches(row) {
        if (filter === "installed") return row.installed
        if (filter === "ui") return row.supportsUi
        if (filter === "en") return row.supportsEn
        return true
    }

    ColumnLayout {
        id: col
        x: 44
        y: 40
        width: Math.min(page.width - 88, 1000)
        spacing: 22

        PageHeader {
            Layout.fillWidth: true
            title: page.t.models_title
            subtitle: page.t.models_subtitle
            ActionButton {
                text: page.t.open_folder
                icon: "folder"
                variant: "ghost"
                compact: true
                onClicked: backend.openModelsFolder()
            }
        }

        // What the two colours mean.
        Rectangle {
            Layout.fillWidth: true
            radius: Theme.radiusSmall
            color: Theme.surfaceSunk
            border.width: 1
            border.color: Theme.line
            implicitHeight: legend.implicitHeight + 28
            ColumnLayout {
                id: legend
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.margins: 18
                spacing: 8
                RowLayout {
                    spacing: 22
                    Row {
                        spacing: 8
                        Rectangle { width: 18; height: 6; radius: 3; color: Theme.accuracy; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: page.t.legend_accuracy; color: Theme.ink; font.family: Theme.body; font.pixelSize: 13 }
                    }
                    Row {
                        spacing: 8
                        Rectangle { width: 18; height: 6; radius: 3; color: Theme.speed; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: page.t.legend_speed; color: Theme.ink; font.family: Theme.body; font.pixelSize: 13 }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: page.t.legend_note
                    color: Theme.muted
                    font.family: Theme.body
                    font.pixelSize: 13
                    lineHeight: 1.3
                    wrapMode: Text.WordWrap
                }
            }
        }

        Segmented {
            // "All", "Downloaded", the interface language, and English when that's a different one.
            options: {
                let o = [{ value: "all", label: page.t.filter_all },
                         { value: "installed", label: page.t.filter_installed },
                         { value: "ui", label: backend.uiLanguageName }]
                if (i18n.code !== "en")
                    o.push({ value: "en", label: "English" })
                return o
            }
            current: page.filter
            onPicked: v => page.filter = v
        }

        GridLayout {
            id: grid
            Layout.fillWidth: true
            columns: col.width > 760 ? 2 : 1
            columnSpacing: 18
            rowSpacing: 18

            Repeater {
                model: modelsModel
                delegate: ModelCard {
                    required property var model
                    row: model
                    visible: page.matches(model)
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 1
                }
            }
        }

        Text {
            Layout.fillWidth: true
            visible: page.filter === "installed" && backend.installedCount === 0
            text: page.t.none_installed
            color: Theme.muted
            font.family: Theme.body
            font.pixelSize: 14
        }
    }
}
