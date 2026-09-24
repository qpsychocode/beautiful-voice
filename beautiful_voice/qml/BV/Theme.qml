pragma Singleton
import QtQuick

// Design tokens. Blue always means accuracy, pink always means speed;
// the black pill is the one shape the whole app is built around.
QtObject {
    id: theme

    property bool dark: false

    // Brand
    readonly property color onyx: "#101019"
    readonly property color onyxRaised: "#1D1D2A"
    readonly property color onyxLine: "#2B2B3C"
    readonly property color cornflower: dark ? "#8EA6FF" : "#7C9CF5"
    readonly property color blush: dark ? "#F4A3C8" : "#F4A6C6"
    readonly property color blueText: dark ? "#AFC0FF" : "#3E58BE"
    readonly property color pinkText: dark ? "#F7B5D2" : "#A93D72"

    // Primary actions: the black pill in light mode, a pale one in dark mode
    readonly property color primary: dark ? "#ECEBF7" : onyx
    readonly property color primaryHover: dark ? "#FFFFFF" : "#20202E"
    readonly property color primaryPressed: dark ? "#D9D8EA" : "#26263A"
    readonly property color primaryInk: dark ? "#101019" : "#F4F3FC"
    readonly property color primaryAccent: dark ? "#B4407A" : blush

    // Meters, validated for contrast and color-vision separation
    readonly property color accuracy: dark ? "#6F8CF2" : "#6C8CF0"
    readonly property color speed: dark ? "#CC6699" : "#EC86B4"

    // Surfaces and ink
    readonly property color bg: dark ? "#11121E" : "#F3F4FB"
    readonly property color sidebar: dark ? "#0C0D17" : "#E9EBF7"
    readonly property color surface: dark ? "#191A2A" : "#FFFFFF"
    readonly property color surfaceSunk: dark ? "#141524" : "#F6F7FD"
    readonly property color hover: dark ? "#22233A" : "#EEF0FA"
    readonly property color line: dark ? "#282A42" : "#E1E4F2"
    readonly property color lineStrong: dark ? "#393C5C" : "#CBD1EB"
    readonly property color track: dark ? "#25273E" : "#EAECF7"
    readonly property color ink: dark ? "#EEEDF8" : "#1E1F35"
    readonly property color muted: dark ? "#A2A5C3" : "#666987"
    readonly property color faint: dark ? "#6E7195" : "#9A9EBD"
    readonly property color danger: dark ? "#FF8FA8" : "#BE2F58"

    // Dusk: the soft blue-to-pink wash behind the hero
    readonly property color duskA: dark ? "#1C2448" : "#DCE4FF"
    readonly property color duskB: dark ? "#35203D" : "#FBDDEC"

    function mix(a, b, t) {
        return Qt.rgba(a.r + (b.r - a.r) * t, a.g + (b.g - a.g) * t, a.b + (b.b - a.b) * t, a.a + (b.a - a.a) * t)
    }

    function pick(candidates) {
        const families = Qt.fontFamilies()
        for (let i = 0; i < candidates.length; ++i)
            if (families.indexOf(candidates[i]) >= 0)
                return candidates[i]
        return candidates[candidates.length - 1]
    }

    // Type: an optical serif italic for titles, Segoe UI Variable for reading,
    // Bahnschrift (DIN-like) for numbers, the timer and keycaps.
    readonly property string display: pick(["Sitka Display", "Sitka", "Iowan Old Style", "Georgia"])
    readonly property string body: pick(["Segoe UI Variable Text", "Segoe UI Variable", "Segoe UI", "SF Pro Text", "Inter", "Arial"])
    readonly property string bodyStrong: pick(["Segoe UI Variable Display", "Segoe UI Variable", "Segoe UI", "SF Pro Display", "Inter", "Arial"])
    readonly property string numeric: pick(["Bahnschrift", "DIN Alternate", "Segoe UI Variable Display", "Arial"])

    readonly property int radius: 18
    readonly property int radiusSmall: 11
}
