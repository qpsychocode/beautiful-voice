import QtQuick
import QtQuick.Layouts

Flickable {
    id: page
    readonly property var t: i18n.t
    readonly property var s: backend.settings

    contentHeight: col.implicitHeight + 80
    clip: true
    boundsBehavior: Flickable.StopAtBounds

    component Section: ColumnLayout {
        id: section
        property string title: ""
        default property alias rows: box.data
        Layout.fillWidth: true
        spacing: 10
        Text {
            text: section.title
            color: Theme.ink
            font.family: Theme.display
            font.italic: Theme.italicTitles
            font.pixelSize: 22
        }
        Rectangle {
            Layout.fillWidth: true
            radius: Theme.radius
            color: Theme.surface
            border.width: 1
            border.color: Theme.line
            implicitHeight: box.implicitHeight + 8
            ColumnLayout {
                id: box
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.topMargin: 4
                anchors.leftMargin: 22
                anchors.rightMargin: 22
                spacing: 0
            }
        }
    }

    ColumnLayout {
        id: col
        x: 44
        y: 40
        width: Math.min(page.width - 88, 820)
        spacing: 30

        PageHeader {
            Layout.fillWidth: true
            title: page.t.settings_title
        }

        Section {
            title: page.t.sec_hotkey
            SettingRow {
                label: page.t.set_hotkey
                hint: backend.capturingHotkey ? page.t.set_hotkey_capture : (backend.hotkeyError !== "" ? backend.hotkeyError : page.t.set_hotkey_hint)
                Row {
                    spacing: 12
                    Keycaps {
                        anchors.verticalCenter: parent.verticalCenter
                        visible: !backend.capturingHotkey
                        keys: backend.hotkeyKeys
                    }
                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        visible: backend.capturingHotkey
                        height: 30
                        width: waiting.implicitWidth + 24
                        radius: 15
                        color: Qt.rgba(Theme.blush.r, Theme.blush.g, Theme.blush.b, 0.22)
                        Text {
                            id: waiting
                            anchors.centerIn: parent
                            text: page.t.set_hotkey_waiting
                            color: Theme.pinkText
                            font.family: Theme.body
                            font.pixelSize: 13
                        }
                    }
                    ActionButton {
                        anchors.verticalCenter: parent.verticalCenter
                        text: backend.capturingHotkey ? page.t.cancel : page.t.change
                        variant: "secondary"
                        compact: true
                        onClicked: backend.captureHotkey(!backend.capturingHotkey)
                    }
                }
            }
            SettingRow {
                label: page.t.set_mode
                hint: page.s.hotkey_mode === "hold" ? page.t.set_mode_hold_hint : page.t.set_mode_toggle_hint
                last: true
                Segmented {
                    options: [{ value: "toggle", label: page.t.mode_toggle }, { value: "hold", label: page.t.mode_hold }]
                    current: page.s.hotkey_mode
                    onPicked: v => backend.setSetting("hotkey_mode", v)
                }
            }
        }

        Section {
            title: page.t.sec_recognition
            SettingRow {
                label: page.t.set_mic
                Dropdown {
                    width: 280
                    options: backend.microphones
                    current: page.s.input_device
                    onPicked: v => backend.setSetting("input_device", v)
                }
            }
            SettingRow {
                label: page.t.set_language
                hint: page.t.set_language_hint
                Dropdown {
                    width: 280
                    options: backend.speechLanguages
                    current: page.s.language
                    onPicked: v => backend.setSetting("language", v)
                }
            }
            SettingRow {
                label: page.t.set_live
                hint: page.t.set_live_hint
                Toggle {
                    checked: page.s.live_transcription
                    onToggled: v => backend.setSetting("live_transcription", v)
                }
            }
            SettingRow {
                label: page.t.set_device
                hint: backend.computeHint
                Segmented {
                    options: [{ value: "auto", label: page.t.device_auto }, { value: "cpu", label: page.t.device_cpu }]
                    current: page.s.compute_device === "cpu" ? "cpu" : "auto"
                    onPicked: v => backend.setSetting("compute_device", v)
                }
            }
            SettingRow {
                label: page.t.set_sounds
                last: true
                Toggle {
                    checked: page.s.sounds
                    onToggled: v => backend.setSetting("sounds", v)
                }
            }
        }

        Section {
            title: page.t.sec_insert
            SettingRow {
                label: page.t.set_insert
                hint: page.s.insert_method === "type" ? page.t.insert_type_hint : page.t.insert_paste_hint
                Segmented {
                    options: [{ value: "paste", label: page.t.insert_paste }, { value: "type", label: page.t.insert_type }]
                    current: page.s.insert_method
                    onPicked: v => backend.setSetting("insert_method", v)
                }
            }
            SettingRow {
                label: page.t.set_restore
                hint: page.t.set_restore_hint
                visible: page.s.insert_method === "paste"
                Toggle {
                    checked: page.s.restore_clipboard
                    onToggled: v => backend.setSetting("restore_clipboard", v)
                }
            }
            SettingRow {
                label: page.t.set_space
                hint: page.t.set_space_hint
                last: true
                Toggle {
                    checked: page.s.trailing_space
                    onToggled: v => backend.setSetting("trailing_space", v)
                }
            }
        }

        Section {
            title: page.t.sec_history
            SettingRow {
                label: page.t.set_history_limit
                hint: page.t.set_history_limit_hint
                last: true
                Stepper {
                    value: page.s.history_limit
                    from: 1
                    to: 1000
                    onValueEdited: v => backend.setSetting("history_limit", v)
                }
            }
        }

        Section {
            title: page.t.sec_look
            SettingRow {
                label: page.t.set_theme
                Segmented {
                    options: [{ value: "light", label: page.t.theme_light }, { value: "dark", label: page.t.theme_dark }]
                    current: page.s.theme
                    onPicked: v => backend.setSetting("theme", v)
                }
            }
            SettingRow {
                label: page.t.set_ui_language
                last: true
                Dropdown {
                    width: 220
                    options: backend.uiLanguages
                    current: page.s.ui_language
                    onPicked: v => backend.setSetting("ui_language", v)
                }
            }
        }

        Section {
            title: page.t.sec_system
            SettingRow {
                visible: backend.isWindows
                label: page.t.set_autostart
                hint: page.t.set_autostart_hint
                Toggle {
                    checked: page.s.autostart
                    onToggled: v => backend.setSetting("autostart", v)
                }
            }
            SettingRow {
                label: page.t.set_minimized
                hint: page.t.set_minimized_hint
                Toggle {
                    checked: page.s.start_minimized
                    onToggled: v => backend.setSetting("start_minimized", v)
                }
            }
            SettingRow {
                label: page.t.set_mirror
                hint: page.t.set_mirror_hint
                last: true
                Segmented {
                    options: [{ value: "auto", label: page.t.source_auto }, { value: "mirror", label: "GitHub" },
                              { value: "huggingface", label: "Hugging Face" }]
                    current: page.s.model_source
                    onPicked: v => backend.setSetting("model_source", v)
                }
            }
        }

        Section {
            title: page.t.sec_about
            SettingRow {
                label: "Beautiful Voice " + backend.version
                hint: page.t.about_hint
                last: true
                Row {
                    spacing: 8
                    ActionButton {
                        text: "GitHub"
                        icon: "external"
                        variant: "secondary"
                        compact: true
                        onClicked: backend.openRepo()
                    }
                    ActionButton {
                        text: page.t.open_data
                        icon: "folder"
                        variant: "ghost"
                        compact: true
                        onClicked: backend.openDataFolder()
                    }
                }
            }
        }
    }
}
