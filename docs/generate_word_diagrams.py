from pathlib import Path
import html


OUT_DIR = Path(__file__).resolve().parent / "word-diagrams"


def esc(text):
    return html.escape(str(text))


class Svg:
    def __init__(self, width, height, background="#ffffff"):
        self.width = width
        self.height = height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<rect x="0" y="0" width="{width}" height="{height}" fill="{background}" />',
            '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="#4b5563"/></marker></defs>',
        ]

    def rect(self, x, y, w, h, text, fill, stroke, text_color="#111827", radius=14, font_size=16):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" ry="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        lines = str(text).split("\n")
        total = len(lines)
        start_y = y + (h / 2) - ((total - 1) * (font_size + 4) / 2) + 5
        for i, line in enumerate(lines):
            ly = start_y + i * (font_size + 4)
            self.parts.append(
                f'<text x="{x + w/2}" y="{ly}" text-anchor="middle" font-family="Arial, sans-serif" font-size="{font_size}" fill="{text_color}">{esc(line)}</text>'
            )

    def cylinder(self, x, y, w, h, text, fill, stroke, text_color="#111827"):
        self.parts.append(
            f'<ellipse cx="{x + w/2}" cy="{y + 14}" rx="{w/2}" ry="14" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        self.parts.append(
            f'<rect x="{x}" y="{y + 14}" width="{w}" height="{h - 28}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        self.parts.append(
            f'<ellipse cx="{x + w/2}" cy="{y + h - 14}" rx="{w/2}" ry="14" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        self.parts.append(
            f'<text x="{x + w/2}" y="{y + h/2 + 5}" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" fill="{text_color}">{esc(text)}</text>'
        )

    def diamond(self, x, y, w, h, text, fill, stroke, text_color="#111827"):
        cx = x + w / 2
        cy = y + h / 2
        points = f"{cx},{y} {x + w},{cy} {cx},{y + h} {x},{cy}"
        self.parts.append(
            f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        lines = str(text).split("\n")
        start_y = cy - (len(lines) - 1) * 10 / 2 + 5
        for i, line in enumerate(lines):
            self.parts.append(
                f'<text x="{cx}" y="{start_y + i * 18}" text-anchor="middle" font-family="Arial, sans-serif" font-size="15" fill="{text_color}">{esc(line)}</text>'
            )

    def actor(self, x, y, label, stroke="#b45309", fill="#fff7ed"):
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="18" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        self.parts.append(f'<line x1="{x}" y1="{y+18}" x2="{x}" y2="{y+58}" stroke="{stroke}" stroke-width="2"/>')
        self.parts.append(f'<line x1="{x-22}" y1="{y+30}" x2="{x+22}" y2="{y+30}" stroke="{stroke}" stroke-width="2"/>')
        self.parts.append(f'<line x1="{x}" y1="{y+58}" x2="{x-20}" y2="{y+88}" stroke="{stroke}" stroke-width="2"/>')
        self.parts.append(f'<line x1="{x}" y1="{y+58}" x2="{x+20}" y2="{y+88}" stroke="{stroke}" stroke-width="2"/>')
        self.parts.append(
            f'<text x="{x}" y="{y+112}" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" fill="#78350f">{esc(label)}</text>'
        )

    def line(self, x1, y1, x2, y2, color="#4b5563", width=2, dashed=False, label=None, label_x=None, label_y=None):
        dash = ' stroke-dasharray="7,5"' if dashed else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}" marker-end="url(#arrow)"{dash}/>'
        )
        if label:
            lx = label_x if label_x is not None else (x1 + x2) / 2
            ly = label_y if label_y is not None else (y1 + y2) / 2 - 6
            self.parts.append(
                f'<text x="{lx}" y="{ly}" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="{color}">{esc(label)}</text>'
            )

    def title(self, text):
        self.parts.append(
            f'<text x="{self.width/2}" y="32" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#1f2937">{esc(text)}</text>'
        )

    def save(self, path):
        path.write_text("".join(self.parts) + "</svg>", encoding="utf-8")


def architecture():
    s = Svg(1400, 820)
    s.title("System Architecture")
    s.actor(100, 170, "Patient")
    s.actor(100, 360, "Doctor")
    s.actor(100, 550, "Admin")
    s.rect(220, 300, 220, 90, "Web Browser UI", "#e0f2fe", "#0284c7")
    s.rect(500, 300, 240, 90, "Flask Web\nApplication", "#dcfce7", "#16a34a")
    s.rect(820, 110, 200, 70, "Authentication", "#dbeafe", "#2563eb")
    s.rect(820, 200, 200, 70, "Prediction", "#dbeafe", "#2563eb")
    s.rect(820, 290, 200, 70, "Patient Module", "#dbeafe", "#2563eb")
    s.rect(820, 380, 200, 70, "Doctor Module", "#dbeafe", "#2563eb")
    s.rect(820, 470, 200, 70, "Admin Module", "#dbeafe", "#2563eb")
    s.rect(820, 560, 200, 70, "Feedback", "#dbeafe", "#2563eb")
    s.rect(1080, 160, 210, 80, "ML Model + Scaler", "#f3e8ff", "#7c3aed")
    s.cylinder(1080, 300, 210, 110, "SQLite Database", "#fee2e2", "#dc2626")
    s.rect(1080, 460, 210, 70, "PDF Generator", "#fef3c7", "#d97706")
    s.rect(1080, 560, 210, 70, "SMTP Email Service", "#fef3c7", "#d97706")
    for y in (345, 405, 565):
        pass
    s.line(118, 170, 220, 330, "#0f766e")
    s.line(118, 360, 220, 345, "#0f766e")
    s.line(118, 550, 220, 360, "#0f766e")
    s.line(440, 345, 500, 345, "#2563eb")
    for cy in (145, 235, 325, 415, 505):
        s.line(740, 345, 820, cy, "#4f46e5")
    s.line(740, 345, 820, 595, "#4f46e5")
    s.line(1020, 235, 1080, 200, "#7c3aed")
    for sy in (145, 235, 325, 415, 505, 595):
        s.line(1020, sy, 1080, 355, "#dc2626")
    s.line(1020, 595, 1080, 495, "#d97706")
    s.line(1020, 595, 1080, 595, "#d97706")
    return s


def dfd_level_0():
    s = Svg(1100, 620)
    s.title("DFD Level 0")
    s.actor(120, 180, "Patient")
    s.actor(120, 340, "Doctor")
    s.actor(120, 500, "Admin")
    s.rect(380, 240, 320, 120, "CardioGuard System", "#ecfeff", "#0891b2", radius=20, font_size=22)
    s.rect(820, 260, 180, 90, "Email Service", "#f3e8ff", "#7c3aed")
    s.line(140, 180, 380, 270, "#0f766e")
    s.line(140, 340, 380, 300, "#0f766e")
    s.line(140, 500, 380, 330, "#0f766e")
    s.line(700, 285, 820, 285, "#7c3aed")
    s.line(820, 325, 700, 325, "#7c3aed")
    return s


def dfd_level_1():
    s = Svg(1500, 900)
    s.title("DFD Level 1")
    s.actor(100, 190, "Patient")
    s.actor(100, 430, "Doctor")
    s.actor(100, 670, "Admin")
    s.rect(260, 100, 240, 80, "1.0 Registration\nand Login", "#dbeafe", "#2563eb")
    s.rect(260, 220, 240, 80, "2.0 Prediction\nManagement", "#dcfce7", "#16a34a")
    s.rect(260, 340, 240, 80, "3.0 History\nand Report", "#dcfce7", "#16a34a")
    s.rect(260, 460, 240, 80, "4.0 Doctor\nServices", "#dbeafe", "#2563eb")
    s.rect(260, 580, 240, 80, "5.0 Admin\nManagement", "#dbeafe", "#2563eb")
    s.rect(260, 700, 240, 80, "6.0 Feedback", "#fef3c7", "#d97706")
    s.cylinder(650, 70, 190, 95, "Patients", "#fee2e2", "#dc2626")
    s.cylinder(650, 190, 190, 95, "Doctors", "#fee2e2", "#dc2626")
    s.cylinder(650, 310, 190, 95, "Predictions", "#fee2e2", "#dc2626")
    s.cylinder(650, 430, 190, 95, "Admins", "#fee2e2", "#dc2626")
    s.cylinder(650, 550, 190, 95, "Feedback", "#fee2e2", "#dc2626")
    s.rect(980, 220, 220, 80, "ML Model", "#ede9fe", "#7c3aed")
    s.rect(980, 360, 220, 80, "PDF / Email Output", "#ede9fe", "#7c3aed")
    s.line(120, 190, 260, 140, "#0f766e")
    s.line(120, 190, 260, 260, "#0f766e")
    s.line(120, 190, 260, 380, "#0f766e")
    s.line(120, 190, 260, 740, "#0f766e")
    s.line(120, 430, 260, 500, "#0f766e")
    s.line(120, 670, 260, 620, "#0f766e")
    mapping = [
        ((500, 140), (650, 118)),
        ((500, 140), (650, 478)),
        ((500, 260), (650, 118)),
        ((500, 260), (650, 238)),
        ((500, 260), (650, 358)),
        ((500, 380), (650, 118)),
        ((500, 380), (650, 358)),
        ((500, 500), (650, 238)),
        ((500, 500), (650, 358)),
        ((500, 620), (650, 118)),
        ((500, 620), (650, 238)),
        ((500, 620), (650, 358)),
        ((500, 620), (650, 478)),
        ((500, 620), (650, 598)),
        ((500, 740), (650, 598)),
    ]
    for start, end in mapping:
        s.line(start[0], start[1], end[0], end[1], "#64748b")
    s.line(500, 260, 980, 260, "#7c3aed")
    s.line(500, 380, 980, 400, "#7c3aed")
    return s


def dfd_level_2():
    s = Svg(1600, 520)
    s.title("DFD Level 2 - Prediction Process")
    s.actor(80, 250, "Patient")
    s.rect(170, 210, 160, 70, "Enter Health\nDetails", "#dcfce7", "#16a34a")
    s.rect(370, 210, 160, 70, "Validate\nInput", "#dcfce7", "#16a34a")
    s.rect(570, 210, 160, 70, "Scale Input\nData", "#dcfce7", "#16a34a")
    s.rect(770, 210, 160, 70, "Run ML\nPrediction", "#dcfce7", "#16a34a")
    s.rect(970, 210, 160, 70, "Generate Risk\nResult", "#dcfce7", "#16a34a")
    s.diamond(1170, 190, 150, 110, "High Risk?", "#fef3c7", "#d97706")
    s.rect(1360, 120, 170, 70, "Fetch Doctor\nSuggestions", "#dbeafe", "#2563eb")
    s.cylinder(1360, 220, 170, 100, "Doctors", "#fee2e2", "#dc2626")
    s.rect(1360, 360, 170, 70, "Show Low Risk\nAdvice", "#dbeafe", "#2563eb")
    s.cylinder(970, 360, 160, 100, "Predictions", "#fee2e2", "#dc2626")
    s.rect(1170, 360, 160, 70, "Return Result\nto Patient", "#dcfce7", "#16a34a")
    s.line(98, 250, 170, 245, "#0f766e")
    for a, b in [(330, 450), (530, 650), (730, 850), (930, 1050)]:
        s.line(a, 245, b, 245, "#16a34a")
    s.line(1130, 245, 1170, 245, "#16a34a")
    s.line(1245, 190, 1445, 190, "#2563eb", label="Yes", label_x=1320, label_y=180)
    s.line(1445, 190, 1445, 220, "#2563eb")
    s.line(1245, 300, 1445, 395, "#2563eb", label="No", label_x=1320, label_y=340)
    s.line(1050, 280, 1050, 360, "#dc2626")
    s.line(1445, 320, 1250, 360, "#2563eb")
    s.line(1360, 395, 1330, 395, "#2563eb")
    s.line(1170, 395, 100, 290, "#0f766e")
    return s


def use_case():
    s = Svg(1500, 980)
    s.title("UML Use Case Diagram")
    s.actor(100, 220, "Patient")
    s.actor(100, 500, "Doctor")
    s.actor(100, 780, "Admin")
    s.parts.append('<rect x="250" y="80" width="1150" height="840" rx="20" ry="20" fill="#f8fafc" stroke="#2563eb" stroke-width="3"/>')
    s.parts.append('<text x="825" y="115" text-anchor="middle" font-family="Arial, sans-serif" font-size="20" font-weight="700" fill="#1e3a8a">CardioGuard System</text>')
    patient_cases = [
        (380, 170, "Register"), (650, 170, "Login"), (920, 170, "Update Profile"),
        (1180, 170, "Predict Heart Disease"), (380, 300, "View Prediction History"),
        (700, 300, "Download PDF Report"), (1040, 300, "Email Prediction Report"),
        (500, 430, "Submit Feedback"), (900, 430, "Reset Password"),
    ]
    doctor_cases = [
        (500, 570, "Doctor Login"), (860, 570, "View Patient Records"),
        (1180, 570, "Search Doctors"), (700, 700, "Doctor Reset Password"),
    ]
    admin_cases = [
        (380, 820, "Admin Login"), (580, 820, "Add Doctor"), (760, 820, "Update Doctor"),
        (940, 820, "Delete Doctor"), (1120, 820, "View Doctors"), (1300, 820, "View Patients"),
    ]
    extra_admin = [(520, 900, "Delete Patient"), (810, 900, "View Feedback"), (1080, 900, "View Analytics")]
    for x, y, label in patient_cases + doctor_cases + admin_cases + extra_admin:
        s.parts.append(f'<ellipse cx="{x}" cy="{y}" rx="110" ry="34" fill="#e0f2fe" stroke="#0284c7" stroke-width="2"/>')
        s.parts.append(f'<text x="{x}" y="{y+5}" text-anchor="middle" font-family="Arial, sans-serif" font-size="15" fill="#0c4a6e">{esc(label)}</text>')
    for x, y, _ in patient_cases:
        s.line(122, 220, x - 110, y, "#6366f1")
    for x, y, _ in doctor_cases:
        s.line(122, 500, x - 110, y, "#6366f1")
    for x, y, _ in admin_cases + extra_admin:
        s.line(122, 780, x - 110, y, "#6366f1")
    return s


def sequence():
    s = Svg(1400, 760)
    s.title("UML Sequence Diagram")
    xs = [120, 380, 680, 960, 1220]
    names = ["Patient", "Web UI", "Flask App", "ML Model", "SQLite DB"]
    colors = ["#fff7ed", "#e0f2fe", "#dcfce7", "#ede9fe", "#fee2e2"]
    strokes = ["#ea580c", "#0284c7", "#16a34a", "#7c3aed", "#dc2626"]
    for x, name, fill, stroke in zip(xs, names, colors, strokes):
        s.rect(x - 70, 70, 140, 50, name, fill, stroke, font_size=16, radius=10)
        s.parts.append(f'<line x1="{x}" y1="120" x2="{x}" y2="700" stroke="#94a3b8" stroke-width="2" stroke-dasharray="8,6"/>')
    msgs = [
        (120, 380, 170, "Enter health details"),
        (380, 680, 240, "POST /predict"),
        (680, 680, 310, "Validate input"),
        (680, 960, 390, "Scale data and predict"),
        (960, 680, 470, "Risk result + probability"),
        (680, 1220, 550, "Save prediction"),
        (680, 1220, 620, "Fetch doctor suggestions (if needed)"),
        (1220, 680, 690, "Stored data / doctor list"),
        (680, 380, 740, "Return result"),
        (380, 120, 770, "Show prediction and advice"),
    ]
    for x1, x2, y, label in msgs:
        s.line(x1, y, x2, y, "#334155", label=label)
    return s


def activity():
    s = Svg(900, 1180)
    s.title("UML Activity Diagram")
    s.parts.append('<ellipse cx="450" cy="90" rx="60" ry="28" fill="#fecaca" stroke="#dc2626" stroke-width="2"/>')
    s.parts.append('<text x="450" y="96" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" fill="#7f1d1d">Start</text>')
    s.rect(340, 150, 220, 60, "Open system", "#dbeafe", "#2563eb")
    s.diamond(340, 250, 220, 100, "New user?", "#fef3c7", "#d97706")
    s.rect(340, 390, 220, 60, "Register account", "#dbeafe", "#2563eb")
    s.rect(340, 500, 220, 60, "Login", "#dbeafe", "#2563eb")
    s.diamond(330, 610, 240, 110, "Select role", "#fef3c7", "#d97706")
    s.rect(110, 760, 200, 60, "Patient dashboard", "#dcfce7", "#16a34a")
    s.rect(110, 860, 200, 60, "Enter health details", "#dcfce7", "#16a34a")
    s.rect(110, 960, 200, 60, "Run prediction", "#dcfce7", "#16a34a")
    s.rect(110, 1060, 200, 60, "View history / PDF / Email", "#dcfce7", "#16a34a")
    s.rect(350, 760, 200, 60, "Doctor dashboard", "#e0f2fe", "#0284c7")
    s.rect(350, 860, 200, 60, "View patient records", "#e0f2fe", "#0284c7")
    s.rect(590, 760, 200, 60, "Admin dashboard", "#ede9fe", "#7c3aed")
    s.rect(590, 860, 200, 60, "Manage users and analytics", "#ede9fe", "#7c3aed")
    s.parts.append('<ellipse cx="450" cy="1130" rx="60" ry="28" fill="#fecaca" stroke="#dc2626" stroke-width="2"/>')
    s.parts.append('<text x="450" y="1136" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" fill="#7f1d1d">End</text>')
    for y1, y2 in [(118, 150), (210, 250), (350, 390), (450, 500), (560, 610)]:
        s.line(450, y1, 450, y2, "#334155")
    s.line(450, 350, 450, 390, "#334155", label="Yes", label_x=485, label_y=372)
    s.line(560, 300, 560, 530, "#334155")
    s.line(560, 530, 560, 665, "#334155", label="No", label_x=590, label_y=520)
    s.line(450, 720, 210, 760, "#16a34a", label="Patient", label_x=300, label_y=735)
    s.line(450, 720, 450, 760, "#0284c7", label="Doctor", label_x=495, label_y=740)
    s.line(450, 720, 690, 760, "#7c3aed", label="Admin", label_x=610, label_y=740)
    s.line(210, 820, 210, 860, "#16a34a")
    s.line(210, 920, 210, 960, "#16a34a")
    s.line(210, 1020, 210, 1060, "#16a34a")
    s.line(210, 1120, 450, 1130, "#334155")
    s.line(450, 820, 450, 860, "#0284c7")
    s.line(450, 920, 450, 1130, "#334155")
    s.line(690, 820, 690, 860, "#7c3aed")
    s.line(690, 920, 450, 1130, "#334155")
    return s


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    diagrams = {
        "system-architecture.svg": architecture(),
        "dfd-level-0.svg": dfd_level_0(),
        "dfd-level-1.svg": dfd_level_1(),
        "dfd-level-2.svg": dfd_level_2(),
        "uml-use-case.svg": use_case(),
        "uml-sequence.svg": sequence(),
        "uml-activity.svg": activity(),
    }
    for name, svg in diagrams.items():
        svg.save(OUT_DIR / name)
    print(f"Generated {len(diagrams)} diagrams in {OUT_DIR}")


if __name__ == "__main__":
    main()
