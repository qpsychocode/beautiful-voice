import QtQuick
import QtQuick.Shapes

// Line icons drawn on a 24-unit grid.
Item {
    id: root
    property string name: "mic"
    property color color: "black"
    property real size: 20
    property real stroke: 1.8
    implicitWidth: size
    implicitHeight: size

    readonly property var paths: ({
        "mic": "M12 3.5a3 3 0 0 0-3 3v5.5a3 3 0 0 0 6 0V6.5a3 3 0 0 0-3-3z M18.5 11.5a6.5 6.5 0 0 1-13 0 M12 18v2.5",
        "models": "M12 3.5l8.5 4.5-8.5 4.5-8.5-4.5z M3.5 12.5l8.5 4.5 8.5-4.5 M3.5 16.5l8.5 4.5 8.5-4.5",
        "gauge": "M4.2 17.5a8.5 8.5 0 1 1 15.6 0 M12 15l4-5.5 M12 15.5a0.8 0.8 0 1 0 0.01 0",
        "history": "M12 3.5a8.5 8.5 0 1 1-8.1 6 M3.5 4.5v5h5 M12 8v4.5l3 2",
        "settings": "M4 7.5h9 M17 7.5h3 M4 16.5h3 M11 16.5h9 M15 5.5v4 M9 14.5v4",
        "x": "M6.5 6.5l11 11 M17.5 6.5l-11 11",
        "check": "M5 12.5l4.5 4.5L19 7.5",
        "download": "M12 4v11 M7 10.5l5 5 5-5 M5 20h14",
        "trash": "M4.5 7h15 M10 11v6 M14 11v6 M6.5 7l.9 11.6a2 2 0 0 0 2 1.9h5.2a2 2 0 0 0 2-1.9L17.5 7 M9.5 7V4.5h5V7",
        "copy": "M9 8.5h9.5a1 1 0 0 1 1 1V20a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V9.5a1 1 0 0 1 1-1z M5 15.5V4.5a1 1 0 0 1 1-1h9",
        "arrow": "M5 12h14 M13.5 6.5L19 12l-5.5 5.5",
        "chevron": "M6.5 9.5l5.5 5.5 5.5-5.5",
        "folder": "M3.5 7a1.5 1.5 0 0 1 1.5-1.5h4l2 2h8a1.5 1.5 0 0 1 1.5 1.5v8.5a1.5 1.5 0 0 1-1.5 1.5H5a1.5 1.5 0 0 1-1.5-1.5z",
        "alert": "M12 3.5a8.5 8.5 0 1 0 0.01 0 M12 7.5v5.5 M12 16.3v.2",
        "refresh": "M19.5 12a7.5 7.5 0 1 1-2.2-5.3 M19.5 4v4.5H15",
        "external": "M13.5 4.5h6v6 M19.5 4.5l-8 8 M17.5 14v4.5a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1v-11a1 1 0 0 1 1-1H10",
        "keyboard": "M3.5 7.5a1.5 1.5 0 0 1 1.5-1.5h14a1.5 1.5 0 0 1 1.5 1.5v9a1.5 1.5 0 0 1-1.5 1.5H5a1.5 1.5 0 0 1-1.5-1.5z M7 10h.5 M10.5 10h.5 M14 10h.5 M17 10h.5 M8 14.5h8",
        "stop": "M7.5 7.5h9v9h-9z",
        "record": "M12 7a5 5 0 1 0 0.01 0",
        "sparkle": "M12 3.5l2 6.5 6.5 2-6.5 2-2 6.5-2-6.5-6.5-2 6.5-2z"
    })
    readonly property var filledIcons: ["stop", "record", "sparkle"]
    readonly property bool filled: filledIcons.indexOf(name) >= 0

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            scale: Qt.size(root.size / 24, root.size / 24)
            strokeColor: root.filled ? "transparent" : root.color
            strokeWidth: root.stroke
            fillColor: root.filled ? root.color : "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: root.paths[root.name] || "" }
        }
    }
}
