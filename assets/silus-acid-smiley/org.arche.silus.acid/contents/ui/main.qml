// Smiley acid temporaire — récompense de l'auto-audit Silus. Aucune I/O, aucun réseau.
import QtQuick
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: root
    preferredRepresentation: fullRepresentation

    fullRepresentation: Rectangle {
        implicitWidth: 480
        implicitHeight: 540
        color: "#0b0b0b"
        property real t: 0

        Timer { interval: 33; running: true; repeat: true; onTriggered: parent.t += 0.05 }

        Canvas {
            id: c
            anchors.horizontalCenter: parent.horizontalCenter
            y: 16
            width: 420; height: 420
            property real t: parent.t
            onTChanged: requestPaint()
            onPaint: {
                const ctx = getContext("2d");
                ctx.reset();
                const cx = width / 2, cy = height / 2, R = 190;
                // halo pulsant
                const pulse = 6 + 4 * Math.sin(t * 2);
                ctx.fillStyle = "rgba(230,255,0,0.18)";
                ctx.beginPath(); ctx.arc(cx, cy, R + pulse * 2, 0, 2 * Math.PI); ctx.fill();
                // visage jaune fluo
                ctx.fillStyle = "#e6ff00";
                ctx.strokeStyle = "#000"; ctx.lineWidth = 8;
                ctx.beginPath(); ctx.arc(cx, cy, R, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
                // yeux hypnotiques : spirales qui tournent en sens opposés
                [[-68, 1], [68, -1]].forEach(function (e) {
                    const ex = cx + e[0], ey = cy - 55;
                    ctx.fillStyle = "#000";
                    ctx.beginPath(); ctx.ellipse(ex - 30, ey - 40, 60, 80); ctx.fill();
                    ctx.strokeStyle = "#e6ff00"; ctx.lineWidth = 3.5;
                    ctx.beginPath();
                    for (let a = 0; a < 6 * Math.PI; a += 0.15) {
                        const r = 2 + a * 1.45;
                        const ang = a + e[1] * t * 3;
                        const x = ex + r * Math.cos(ang), y = ey + r * 1.3 * Math.sin(ang);
                        if (a === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                    }
                    ctx.stroke();
                });
                // sourire gigantesque
                ctx.fillStyle = "#000";
                ctx.beginPath();
                ctx.moveTo(cx - 140, cy + 25);
                ctx.quadraticCurveTo(cx, cy + 205 + 8 * Math.sin(t * 2), cx + 140, cy + 25);
                ctx.quadraticCurveTo(cx, cy + 95, cx - 140, cy + 25);
                ctx.fill();
                // fossettes
                ctx.lineWidth = 7; ctx.strokeStyle = "#000";
                ctx.beginPath(); ctx.arc(cx - 150, cy + 30, 16, Math.PI * 0.6, Math.PI * 1.4); ctx.stroke();
                ctx.beginPath(); ctx.arc(cx + 150, cy + 30, 16, -Math.PI * 0.4, Math.PI * 0.4); ctx.stroke();
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 26
            text: "SILUS — SANDBOX AUDIT COMPLETE ☺"
            color: Qt.hsla((parent.t * 0.08) % 1, 1, 0.6, 1)
            font.pixelSize: 24
            font.bold: true
            font.family: "monospace"
        }
    }
}
