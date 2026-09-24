import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import BV

ApplicationWindow {
    id: window
    readonly property var t: i18n.t
    property string page: "dictate"

    width: 1140
    height: 780
    minimumWidth: 920
    minimumHeight: 620
    title: "Beautiful Voice"
    color: Theme.bg
    visible: false

    onClosing: close => {
        // Closing the window keeps the app (and the hotkey) running in the tray.
        close.accepted = false
        window.hide()
        backend.windowHidden()
    }

    function go(name) { page = name }

    Binding {
        target: Theme
        property: "dark"
        value: backend.settings.theme === "dark"
    }
    Binding {
        target: Theme
        property: "uiLang"
        value: i18n.code
    }

    Connections {
        target: backend
        function onNavigateRequested(name) { window.go(name) }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Sidebar
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 244
            color: Theme.sidebar

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                anchors.topMargin: 24
                spacing: 4

                // Wordmark
                RowLayout {
                    Layout.leftMargin: 6
                    Layout.bottomMargin: 26
                    spacing: 12
                    LogoMark { s: 38 }
                    ColumnLayout {
                        spacing: -4
                        Text {
                            text: "Beautiful"
                            color: Theme.ink
                            font.family: Theme.brandSerif
                            font.italic: true
                            font.pixelSize: 23
                        }
                        Text {
                            text: "VOICE"
                            color: Theme.muted
                            font.family: Theme.bodyStrong
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                            font.letterSpacing: 4.2
                        }
                    }
                }

                NavItem { Layout.fillWidth: true; text: window.t.nav_dictate; icon: "mic"; selected: window.page === "dictate"; onClicked: window.go("dictate") }
                NavItem { Layout.fillWidth: true; text: window.t.nav_models; icon: "models"; selected: window.page === "models"; onClicked: window.go("models")
                          badge: backend.downloadingCount > 0 ? String(backend.downloadingCount) : "" }
                NavItem { Layout.fillWidth: true; text: window.t.nav_bench; icon: "gauge"; selected: window.page === "bench"; onClicked: window.go("bench") }
                NavItem { Layout.fillWidth: true; text: window.t.nav_history; icon: "history"; selected: window.page === "history"; onClicked: window.go("history")
                          badge: historyModel.count > 0 ? String(historyModel.count) : "" }
                NavItem { Layout.fillWidth: true; text: window.t.nav_settings; icon: "settings"; selected: window.page === "settings"; onClicked: window.go("settings") }

                Item { Layout.fillHeight: true }

                // A new version is out: shown only then.
                Rectangle {
                    Layout.fillWidth: true
                    Layout.bottomMargin: 8
                    visible: ["available", "downloading", "ready", "error"].indexOf(updater.state) >= 0
                    radius: 14
                    implicitHeight: upd.implicitHeight + 28
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: Theme.duskA }
                        GradientStop { position: 1; color: Theme.duskB }
                    }

                    ColumnLayout {
                        id: upd
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.margins: 14
                        spacing: 10

                        RowLayout {
                            spacing: 8
                            Icon { name: "sparkle"; size: 14; color: Theme.pinkText }
                            Text {
                                Layout.fillWidth: true
                                text: window.t.update_available.replace("{version}", updater.version)
                                color: Theme.ink
                                font.family: Theme.body
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                wrapMode: Text.WordWrap
                            }
                        }
                        ColumnLayout {
                            visible: updater.state === "downloading"
                            spacing: 6
                            Rectangle {
                                Layout.fillWidth: true
                                height: 5
                                radius: 3
                                color: Qt.rgba(1, 1, 1, Theme.dark ? 0.15 : 0.7)
                                Rectangle {
                                    height: parent.height
                                    radius: 3
                                    width: Math.max(height, parent.width * updater.progress)
                                    color: Theme.primary
                                }
                            }
                            Text {
                                text: window.t.update_downloading.replace("{pct}", Math.round(updater.progress * 100))
                                color: Theme.muted
                                font.family: Theme.body
                                font.pixelSize: 12
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            visible: updater.state === "error"
                            text: window.t.update_failed.replace("{error}", updater.error)
                            color: Theme.danger
                            font.family: Theme.body
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                            maximumLineCount: 3
                            elide: Text.ElideRight
                        }
                        ActionButton {
                            Layout.fillWidth: true
                            visible: updater.state !== "downloading"
                            compact: true
                            icon: updater.state === "ready" ? "refresh" : "download"
                            text: updater.state === "ready" ? window.t.update_install
                                : updater.state === "error" ? window.t.update_retry
                                : window.t.update_download
                            onClicked: updater.state === "ready" ? updater.install() : updater.download()
                        }
                    }
                }

                // Status: which model is listening and how to call it.
                Rectangle {
                    Layout.fillWidth: true
                    radius: 14
                    color: Theme.surface
                    border.width: 1
                    border.color: Theme.line
                    implicitHeight: status.implicitHeight + 28

                    ColumnLayout {
                        id: status
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.margins: 14
                        spacing: 10

                        RowLayout {
                            spacing: 8
                            Rectangle {
                                width: 8; height: 8; radius: 4
                                color: backend.modelStatus === "ready" ? Theme.cornflower
                                     : backend.modelStatus === "loading" ? Theme.blush
                                     : backend.modelStatus === "error" ? Theme.danger : Theme.faint
                                SequentialAnimation on opacity {
                                    running: backend.modelStatus === "loading"
                                    loops: Animation.Infinite
                                    NumberAnimation { to: 0.3; duration: 500 }
                                    NumberAnimation { to: 1; duration: 500 }
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: backend.activeModel.name || window.t.model_none
                                color: Theme.ink
                                font.family: Theme.body
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            text: backend.activeModel.statusText || window.t.model_none_hint
                            color: Theme.muted
                            font.family: Theme.body
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                        }
                        Keycaps { keys: backend.hotkeyKeys; small: true }
                    }
                }
            }
        }

        // Pages
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Repeater {
                model: ["dictate", "models", "bench", "history", "settings"]
                delegate: Loader {
                    required property string modelData
                    anchors.fill: parent
                    readonly property bool current: window.page === modelData
                    active: current || item !== null
                    visible: opacity > 0
                    opacity: current ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: 160 } }
                    sourceComponent: modelData === "dictate" ? dictatePage
                                   : modelData === "models" ? modelsPage
                                   : modelData === "bench" ? benchPage
                                   : modelData === "history" ? historyPage
                                   : settingsPage
                    onLoaded: if (item.navigate) item.navigate.connect(window.go)
                }
            }
        }
    }

    Component { id: dictatePage; DictatePage {} }
    Component { id: modelsPage; ModelsPage {} }
    Component { id: benchPage; BenchPage {} }
    Component { id: historyPage; HistoryPage {} }
    Component { id: settingsPage; SettingsPage {} }
}
