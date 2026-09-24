import QtQuick

// The voice bars. The newest loudness sits in the middle and older values
// ripple outward to both sides, so speech reads as waves leaving the centre.
Item {
    id: root

    property int bars: 21
    property real barWidth: 3
    property real gap: 3
    property real minHeight: 3
    property real level: 0          // live microphone level, 0..1
    property string mode: "idle"    // live | idle | wave | still
    property bool running: visible
    property color fromColor: Theme.cornflower
    property color toColor: Theme.blush

    implicitWidth: bars * barWidth + (bars - 1) * gap
    implicitHeight: 26

    property var heights: []
    property var jitter: []
    property var trail: []
    property real smooth: 0
    property real phase: 0

    Component.onCompleted: {
        let j = []
        let seed = 7
        for (let i = 0; i < bars; ++i) {
            seed = (seed * 9301 + 49297) % 233280
            j.push(0.82 + 0.36 * seed / 233280)
        }
        jitter = j
        tick()
    }

    function tick() {
        phase += 0.11
        const half = Math.ceil(bars / 2)
        const center = (bars - 1) / 2
        let values = []
        if (mode === "live") {
            // Rise fast, fall a little slower: bars feel responsive but not jittery.
            smooth = level > smooth ? smooth + (level - smooth) * 0.65 : smooth + (level - smooth) * 0.28
            let t = trail.slice(0, half - 1)
            t.unshift(smooth)
            trail = t
        }
        for (let i = 0; i < bars; ++i) {
            const d = Math.abs(i - center)
            let v
            if (mode === "live") {
                const k = Math.round(d)
                const past = k < trail.length ? trail[k] : 0
                v = past * (1 - d / (bars * 0.9)) * jitter[i]
            } else if (mode === "wave") {
                v = 0.18 + 0.5 * (0.5 + 0.5 * Math.sin(phase * 1.7 - i * 0.55)) * (1 - d / bars)
            } else if (mode === "still") {
                v = 0
            } else {
                v = (0.12 + 0.2 * (0.5 + 0.5 * Math.sin(phase * 0.55 + i * 0.42))) * (1 - 1.4 * d / bars)
            }
            values.push(Math.max(0, Math.min(1, v)))
        }
        heights = values
    }

    Timer {
        interval: 33
        repeat: true
        running: root.running && root.mode !== "still"
        onTriggered: root.tick()
    }

    Row {
        anchors.centerIn: parent
        spacing: root.gap
        Repeater {
            model: root.bars
            Rectangle {
                required property int index
                width: root.barWidth
                radius: width / 2
                anchors.verticalCenter: parent.verticalCenter
                height: root.minHeight + (root.height - root.minHeight) * (root.heights.length > index ? root.heights[index] : 0)
                color: Theme.mix(root.fromColor, root.toColor, index / Math.max(1, root.bars - 1))
                Behavior on height { NumberAnimation { duration: 60 } }
            }
        }
    }
}
