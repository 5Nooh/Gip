"""
Slaaptracker GIP
Nooh Malkaoui
Realtime ademhalingsanalyse met Arduino en PyQt6

"""

#BIBLIOTHEKEN IMPORTEREN
import sys, serial, time
import numpy as np
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

#INSTELLINGEN
PORT, BAUD = "COM3", 9600

#ANALYSE FUNCTIE DIE WAARDES ECHT OMZET IN BETEKENIS
def analyse(bpms):
    geldig = [b for b in bpms if 4 <= b <= 45]

    if len(geldig) < 30:
        return {
            "klaar": False,
            "aantal": len(geldig)
        }

    gem = np.mean(geldig)
    sd = np.std(geldig)

    #Simpele uitlegbare logica (medische bronnen)
    if sd < 1.5:
        stabiliteit = "Zeer stabiel"
        kleur = "#00ff99"
    elif sd < 3:
        stabiliteit = "Normaal"
        kleur = "#64b5f6"
    elif sd < 5:
        stabiliteit = "Onrustig"
        kleur = "#f0a500"
    else:
        stabiliteit = "Zeer onrustig"
        kleur = "#ff4444"

    #Fase (simpel uitgelegd) 
    if gem < 10:
        fase = "Zeer trage ademhaling (diepe rust)"
    elif gem < 16:
        fase = "Diepe slaap"
    elif gem < 20:
        fase = "Lichte slaap"
    else:
        fase = "Actieve / onrustige fase"

    #rend (simpel)
    helling = np.polyfit(range(len(geldig)), geldig, 1)[0]

    if helling > 0.05:
        trend = "Ademhaling versnelt"
    elif helling < -0.05:
        trend = "Ademhaling vertraagt"
    else:
        trend = "Ademhaling stabiel"

    piek_afwijking = abs(gem - 14)
    score = 100 - (sd * 12) - (piek_afwijking * 2)
    score = max(0, min(100, score))

    return {
        "gem": gem,
        "sd": sd,
        "fase": fase,
        "stabiliteit": stabiliteit,
        "kleur": kleur,
        "trend": trend,
        "score": score,
        "klaar": True
    }


#PYQT DASHBOARD
class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()

        self.metend = False
        self.start_time = None
        self.stop_time = None

        self.setWindowTitle("Nooh's Slaaptracker")
        self.setGeometry(200,100,1200,700)
        self.setStyleSheet("QMainWindow{background:#0f0f1a;} QLabel{color:#c0c8e0;}")

        self.bpms, self.tijden, self.waardes = [], [], []
        self.bpms_all = []

        self.init_ui()

        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=0)
        except:
            self.status_label.setText("Geen Arduino verbinding")
            self.ser = None
        time.sleep(2)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_all)
        self.timer.start(50)   

    def start_meting(self):
        self.metend = True
        self.start_time = time.time()
        self.status_label.setText("🟢BEZIG")

    def stop_meting(self):
        self.metend = False
        self.stop_time = time.time()  # bijhouden!
        self.status_label.setText("🔴GESTOPT")

    def reset_meting(self):
        self.bpms.clear()
        self.bpms_all.clear()
        self.tijden.clear()
        self.waardes.clear()
        self.line.set_data([], [])
        self.canvas.draw_idle()
        self.lbl_report.hide()
        self.lbl_score.setText("—")
        self.lbl_stats.setText("Data gereset.")
        self.status_label.setText("🟡KLAAR")
        self.start_time = None
        self.stop_time = None

    #Gebruikersinterface
    def toggle_report(self):
        a = analyse(self.bpms_all)

        if not a or not a.get("klaar"):
            aantal = len(self.bpms_all)
            self.lbl_report.setText(
                f"Nog niet genoeg data voor een rapport.\n"
                f"Huidige metingen: {aantal} / 30"
            )
            self.lbl_report.show()
            return

        uitleg = ""

        if a['stabiliteit'] == "Zeer stabiel":
            uitleg += "Je ademhaling is zeer regelmatig. Dit wijst op een rustige en stabiele slaap.\n\n"
        elif a['stabiliteit'] == "Normaal":
            uitleg += "Je ademhaling vertoont normale variaties, wat typisch is tijdens slaap.\n\n"
        else:
            uitleg += "Je ademhaling is vrij onrustig. Dit kan wijzen op beweging of lichte slaap.\n\n"

        if "Diepe slaap" in a['fase']:
            uitleg += "Je bevond je waarschijnlijk in een diepe slaapfase.\n\n"
        elif "Lichte slaap" in a['fase']:
            uitleg += "Je zat waarschijnlijk in een lichtere slaapfase.\n\n"
        else:
            uitleg += "Je ademhaling wijst op een actievere fase.\n\n"

        #Meetduur correct berekenen
        duur = 0

        einde = self.stop_time if self.stop_time else time.time()
        duur = int(einde - self.start_time) if self.start_time else 0

        minuten = duur // 60
        seconden = duur % 60

        uitleg += f"Gemiddelde ademhaling: {a['gem']:.1f} per minuut\n"
        uitleg += f"Minimum BPM: {min(self.bpms_all):.1f}\n"
        uitleg += f"Maximum BPM: {max(self.bpms_all):.1f}\n"
        uitleg += f"Variatie (SD): {a['sd']:.2f}\n"
        uitleg += f"Stabiliteitsscore: {a['score']:.0f} / 100\n"
        uitleg += f"Totale meetduur: {minuten} min {seconden} sec\n"
        uitleg += f"Aantal geldige metingen: {len(self.bpms_all)}"

        self.lbl_report.setText(uitleg)
        self.lbl_report.show()

    def init_ui(self):
        self.bpms_all = []
       
        main = QWidget()
        self.setCentralWidget(main)
        layout = QHBoxLayout(main)
        layout.setContentsMargins(16,16,16,16)
        layout.setSpacing(16)

        #Grafiek
        self.fig = Figure(facecolor="#0f0f1a")
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#13131f")

        for sp in self.ax.spines.values():
            sp.set_color("#333")

        self.ax.tick_params(colors="#888")
        self.ax.set_title("Realtime Ademhalingssignaal", color="#aaaacc")

        self.ax.set_xlabel("Tijd (s)", color="#888")
        self.ax.set_ylabel("Amplitude (sensorwaarde)", color="#888")
        self.ax.grid(True, alpha=0.2)

        self.line, = self.ax.plot([], [], color="#00ff99", linewidth=1.5)

        layout.addWidget(self.canvas, 3)

        #Rechter zijscherm waar analyse komt
        panel = QWidget()
        panel.setStyleSheet("background:#13131f;border-radius:12px;")
        p = QVBoxLayout(panel)
        p.setContentsMargins(20,24,20,20)
        p.setSpacing(10)

        #START/STOP/RESET knoppen
        self.btn_start = QPushButton("Start meting")
        self.btn_stop = QPushButton("Stop meting")
        self.btn_reset = QPushButton("Reset")

        for b in [self.btn_start, self.btn_stop, self.btn_reset]:
            b.setStyleSheet(
                "QPushButton{background:#1f6feb;color:white;"
                "font-weight:bold;padding:8px;border-radius:6px}"
                "QPushButton:hover{background:#388bfd}")
            p.addWidget(b)

        self.btn_start.clicked.connect(self.start_meting)
        self.btn_stop.clicked.connect(self.stop_meting)
        self.btn_reset.clicked.connect(self.reset_meting)
        p.setContentsMargins(20,24,20,20)
        p.setSpacing(10)

        title = QLabel("Live Analyse")
        title.setStyleSheet("color:#00ff99;font-size:16px;font-weight:bold;")
        p.addWidget(title)

        self.lbl_score = QLabel("Stabiliteitsscore\n—")
        self.lbl_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_score.setStyleSheet(
            "color:#00ff99;font-size:28px;font-weight:bold;"
            "background:#0a0a14;border-radius:10px;padding:18px;")
        p.addWidget(self.lbl_score)

        self.lbl_stats = QLabel("Data verzamelen...")
        self.lbl_stats.setStyleSheet("font-size:13px; font-family:Segoe UI;")
        p.addWidget(self.lbl_stats)

        self.lbl_fase = QLabel("—")
        self.lbl_fase.setWordWrap(True)
        self.lbl_fase.setStyleSheet(
            "color:#a78bfa;font-weight:bold;"
            "background:#1a1228;border-radius:8px;padding:10px;")
        p.addWidget(self.lbl_fase)

        self.lbl_stab = QLabel("—")
        self.lbl_stab.setWordWrap(True)
        self.lbl_stab.setStyleSheet(
            "color:#64b5f6;font-weight:bold;"
            "background:#0e1a28;border-radius:8px;padding:10px;")
        p.addWidget(self.lbl_stab)

        self.status_label = QLabel("🟡KLAAR")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(
            "font-size:14px;font-weight:bold;color:#ffaa00;"
        )
        p.addWidget(self.status_label)

        p.addStretch()

        btn = QPushButton("Rapport bekijken")
        btn.setStyleSheet(
            "QPushButton{background:#1f6feb;color:white;"
            "font-weight:bold;padding:12px;border-radius:8px}"
            "QPushButton:hover{background:#388bfd}")
        p.addWidget(btn)
        btn.clicked.connect(self.toggle_report)

        self.lbl_report = QLabel("")
        self.lbl_report.setWordWrap(True)
        self.lbl_report.setStyleSheet(
            "color:#cccccc;background:#0a0a14;"
            "border-radius:8px;padding:10px;font-size:12px;")
        p.addWidget(self.lbl_report)
        self.lbl_report.hide()

        layout.addWidget(panel, 1)

    #CONSTANTE UPDATES MET LOOP 
    def update_all(self):
        if not self.metend or not self.ser:
            return
        #uitlezing
        while self.ser.in_waiting:
            line = self.ser.readline().decode(errors="ignore").strip()
            parts = line.split(",")
            if len(parts) != 3:
                continue
            try:
                t, w, b = int(parts[0]), float(parts[1]), float(parts[2])
            except:
                continue

            self.tijden.append(t/1000)
            self.waardes.append(w)
            if 4 <= b <= 45:
                self.bpms.append(b)       #voor live (60 sec)
                self.bpms_all.append(b)   #voor volledige analyse

        while self.tijden and self.tijden[-1] - self.tijden[0] > 60:
            self.tijden.pop(0)
            self.waardes.pop(0)
            if self.bpms:
                self.bpms.pop(0)

        #Grafiek updaten
        if len(self.waardes) > 20:
            window = 8
            smooth = np.convolve(
                self.waardes,
                np.ones(window) / window,
                mode='valid'
            )

            #Baseline correction
            smooth = smooth - np.mean(smooth)

            #Kleine ruis verwijderen
            drempel = 1

            smooth = np.where(
                abs(smooth) < drempel,
                0,
                smooth
)
            x_vals = self.tijden[-len(smooth):]

            self.line.set_data(x_vals, smooth)
            self.ax.set_xlim(max(0, x_vals[-1] - 20), x_vals[-1])
            self.ax.relim()
            self.ax.autoscale_view(scaley=True)
            #self.ax.set_ylim(-50, 50)
            self.canvas.draw_idle()

        #Live analyse tijdens meting
        a = analyse(self.bpms_all)

        if not a.get("klaar"):
            self.lbl_stats.setText(
                f"Data verzamelen...\n"
                f"{a['aantal']} / 30 metingen")
            return

        sc = a['score']
        k = "#00ff99" if sc>=70 else "#f0a500" if sc>=40 else "#ff4444"

        self.lbl_score.setText(f"{a['score']:.0f} / 100")
        self.lbl_score.setStyleSheet(
            f"color:{k};font-size:28px;font-weight:bold;"
            "background:#0a0a14;border-radius:10px;padding:18px;")

        self.lbl_stats.setText(
            f"Gemiddelde ademhaling: {a['gem']:.1f} per minuut\n"
            f"Variatie: {a['sd']:.2f}\n"
            f"{a['trend']}"
        )

        self.lbl_fase.setText(f"Slaapfase:\n{a['fase']}")
        self.lbl_stab.setText(f"Stabiliteit:\n{a['stabiliteit']}")

#STARTEN
app = QApplication(sys.argv)
window = Dashboard()
window.show()
sys.exit(app.exec())