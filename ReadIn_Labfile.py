import tkinter as tk
from tkinter import ttk
import pandas as pd
from collections import defaultdict
from tkinter import filedialog, messagebox
import os
import re

MAX_BPS = 4_000_000  # 4 Mbps in Bytes pro Sekunde

#def lade_lab_datei(pfad):
#    daten = []
#    with open(pfad, 'r') as file:
#        for line in file:
#            line = line.strip()
#            if ';' in line:
#                teile = line.split(';')
#                daten.append(teile)
#            else:
#            # Falls Zeilen ohne ';' vorkommen, hier behandeln oder überspringen
#                pass
#    return daten


def lade_lab_datei_ab_start(pfad, start_marker):
    daten = []
    start_lesen = False
    with open(pfad, 'r') as file:
        for line in file:
            line = line.strip()
            # Prüfen, ob die Startmarke in der Zeile vorkommt (case-insensitive)
            if not start_lesen:
                if start_marker.lower() in line.lower():
                    start_lesen = True
                else:
                    continue  # noch nicht gestartet, Zeile ignorieren
            
            # Ab hier werden nur Zeilen verarbeitet, die ein ';' enthalten
            if ';' in line:
                teile = line.split(';')
                daten.append(teile)
            else:
            # Falls Zeilen ohne ';' vorkommen, hier behandeln oder überspringen
                pass

    return daten


def gruppiere_mit_untergruppen(data):
    gruppiert = defaultdict(lambda: defaultdict(list))
    kurz_gruppe = "Kurz (<3 Zeichen)"
    punkt_gruppe = "Mit Punkt"
    kleinbuchstabe_gruppe = "Start mit Kleinbuchstaben"
    
    for eintrag in data:
        # Erster Teil vor Unterstrich im ersten Feld
        erster_teil = eintrag[0].split('_')[0] if '_' in eintrag[0] else eintrag[0]
        
        # Prüfen, ob erster Teil einen Punkt enthält
        if '.' in erster_teil:
            hauptgruppe = punkt_gruppe

        # Prüfen, ob erster Teil mit einem Kleinbuchstaben startet
        elif erster_teil and erster_teil[0].islower():
            hauptgruppe = kleinbuchstabe_gruppe
        
        # Prüfen, ob erster Teil weniger als 3 Buchstaben hat
        elif len(erster_teil) < 3:
            hauptgruppe = kurz_gruppe
        
        else:
            s = erster_teil
            schluessel = s[0]
            i = 1
            while i < len(s):
                # Prüfe, ob wir mindestens 2 Zeichen haben, um Übergänge zu erkennen
                if i > 0:
                    prev_char = s[i-1]
                    curr_char = s[i]

                    # Fall 1: Kleinbuchstabe gefolgt von Großbuchstabe -> stoppen
                    if prev_char.islower() and curr_char.isupper():
                        break

                    # Fall 2: Großbuchstabe gefolgt von Großbuchstabe
                    if prev_char.isupper() and curr_char.isupper():
                        # Suche nächsten Unterstrich ab Position i+1
                        rest = s[i+1:]
                        unterstrich_pos = rest.find('_')
                        if unterstrich_pos != -1:
                            schluessel += s[i] + rest[:unterstrich_pos]
                        else:
                            schluessel += s[i] + rest
                        break
                schluessel += curr_char
                i += 1
            hauptgruppe = schluessel

        if '_' in eintrag[0]:
            untergruppe = eintrag[0].split('_')[0]
        elif '.' in eintrag[0]:
            untergruppe = eintrag[0].split('.')[0]
        else:
            untergruppe = hauptgruppe

        gruppiert[hauptgruppe][untergruppe].append(eintrag)

    return gruppiert


def berechne_bytes_pro_sekunde(gruppierte_daten):
        bytes_per_entry = 4
        hauptgruppe_bps = {}
        untergruppe_bps = {}

        for hauptgruppe, untergruppen in gruppierte_daten.items():
            gesamt_bps_haupt = 0.0
            untergruppe_bps[hauptgruppe] = {}

            for untergruppe, eintraege in untergruppen.items():
                gesamt_bps_unter = 0.0
                for eintrag in eintraege:
                    if len(eintrag) < 2:
                        continue  # falls zweites Feld fehlt

                    # Beispiel zweites Feld: 'XETKS_10ms'
                    zeit_str = eintrag[1]

                    # Suche Zahl vor 'ms'
                    match = re.search(r'(\d+)\s*ms$', zeit_str)
                    if match:
                        ms = int(match.group(1))
                        if ms > 0:
                            bps = (bytes_per_entry * 1000) / ms
                            gesamt_bps_unter += bps
                        else:
                            # ms = 0 vermeiden, sonst Division durch Null
                            pass
                    else:
                        # Kein gültiger ms-Wert gefunden, ggf. ignorieren oder loggen
                        pass

                untergruppe_bps[hauptgruppe][untergruppe] = gesamt_bps_unter
                gesamt_bps_haupt += gesamt_bps_unter

            hauptgruppe_bps[hauptgruppe] = gesamt_bps_haupt

        return hauptgruppe_bps, untergruppe_bps
    

def format_bytes_per_sec(bps):
    if bps >= 1_000_000:
        wert = bps / 1_000_000
        einheit = "MB/s"
    elif bps >= 1_000:
        wert = bps / 1_000
        einheit = "kB/s"
    else:
        wert = bps
        einheit = "B/s"
    return f"{wert:.2f} {einheit}"


def get_untergruppenname(hauptgruppe, untergruppe):
    if untergruppe == hauptgruppe:
        return untergruppe  # Zeige den tatsächlichen Namen
    elif untergruppe and untergruppe.strip() != '':
        return untergruppe
    else:
        return "(keine Untergruppe)"




class AccordionWithCheckbox(tk.Frame):

    def __init__(self, master, hauptgruppe, untergruppen, untergruppen_bps=None, on_selection_change=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.on_selection_change = on_selection_change
        self.untergruppen_bps = untergruppen_bps or {}

        self.hauptgruppe = hauptgruppe
        self.untergruppen = untergruppen
        self.is_expanded = False

        # Frame für Button und Checkbox nebeneinander
        header_frame = tk.Frame(self)
        header_frame.pack(fill='x')

        # Toggle-Button für Ein-/Ausklappen
        self.toggle_button = tk.Button(header_frame, text="v", width=2, command=self.toggle)
        self.toggle_button.pack(side='left')

        # Checkbox für Auswahl der Hauptgruppe
        self.haken_label = tk.Label(header_frame, text='✓', font=('Arial', 10, 'bold'), cursor='hand2')
        self.haken_label.pack(side='left', padx=5)
        self.haken_label.bind("<Button-1>", self.on_haken_click)

        self.hauptgruppen_label = tk.Label(header_frame, text=hauptgruppe, font=('Arial', 10, 'bold'), 
                                       cursor='hand2')
        self.hauptgruppen_label.pack(side='left')
        self.hauptgruppen_label.bind("<Button-1>", self.on_haken_click)

        self.hauptgruppe_selected = True        

        # Frame für Untergruppen, zunächst versteckt
        self.content_frame = tk.Frame(self)
        self.content_frame.pack(fill='x', expand=True)
        self.content_frame.pack_forget()

        # Untergruppen-Checkboxen
        self.subgroup_vars = []
        untergruppen_bps = untergruppen_bps or {}

        for untergruppe, eintraege in sorted(untergruppen.items(), key=lambda x: len(x[1]), reverse=True):
            var = tk.BooleanVar(value=True)
            uname = untergruppe if untergruppe else "(keine Untergruppe)"
            bps_wert = untergruppen_bps.get(untergruppe, 0)
            bps_formatiert = format_bytes_per_sec(bps_wert)
            cb_text = f"{uname} ({len(eintraege)} Einträge, {bps_formatiert})"
            cb = tk.Checkbutton(self.content_frame, text=cb_text, variable=var, command=self.on_untergruppe_toggle)
            cb.pack(anchor='w', padx=20)
            self.subgroup_vars.append((var, untergruppe, eintraege))

        self.update_haken_farbe()


    def toggle(self):
        if self.is_expanded:
            self.content_frame.pack_forget()
            self.toggle_button.config(text="v")
            self.is_expanded = False
        else:
            self.content_frame.pack(fill='x', expand=True)
            self.toggle_button.config(text="^")
            self.is_expanded = True


    def on_haken_click(self, event=None):
        # Alle auswählen oder abwählen, je nach aktuellem Zustand
        neuer_status = not self.hauptgruppe_selected
        self.set_hauptgruppe_status(neuer_status)
        if self.on_selection_change:
        # Verzögere den Aufruf, um sicher zu sein, dass alle Checkboxen aktualisiert sind
            self.after_idle(self.on_selection_change)


    def on_untergruppe_toggle(self):
        alle_ausgewaehlt = all(var.get() for var, _, _ in self.subgroup_vars)
        keine_ausgewaehlt = not any(var.get() for var, _, _ in self.subgroup_vars)

        if alle_ausgewaehlt:
            self.hauptgruppe_selected = True
        elif keine_ausgewaehlt:
            self.hauptgruppe_selected = False
        else:
            self.hauptgruppe_selected = True

        self.update_haken_farbe()
        if self.on_selection_change:
            # Verzögere den Aufruf
            self.after_idle(self.on_selection_change)


    def update_haken_farbe(self):
        # Wenn alle Untergruppen ausgewählt sind, Hauptgruppe auswählen, sonst abwählen oder grauen Haken setzen
        alle_ausgewaehlt = all(var.get() for var, _, _ in self.subgroup_vars)
        keine_ausgewaehlt = not any(var.get() for var, _, _ in self.subgroup_vars)
        
        if alle_ausgewaehlt:
            self.haken_label.config(fg='black', text='✓')  # Schwarzer Haken
        elif keine_ausgewaehlt:
            self.haken_label.config(text='☐', fg='black')  # Kein Haken
        else:
            self.haken_label.config(fg='gray', text='✓')  # Grauer Haken


    def get_hauptgruppe_status(self):
        return self.hauptgruppe_selected
    

    def set_hauptgruppe_status(self, status: bool):
        self.hauptgruppe_selected = status
        # Alle Untergruppen entsprechend setzen
        for var, _, _ in self.subgroup_vars:
            var.set(status)
        self.update_haken_farbe()




class FilterTool(tk.Tk):

    def __init__(self, gruppierte_daten=None):
        super().__init__()
        self.title("Filter Tool mit Suchfunkion")
        self.geometry("700x600")

        original_daten = gruppierte_daten if gruppierte_daten else{}
        self.anzeige_daten = original_daten
        aktueller_dateipfad = None  # Initialisierung

        self.check_vars = []
        
        # Suchfeld
        self.search_label = ttk.Label(self, text="Gruppen suchen:")
        self.search_label.pack(pady=(10,0))
        
        self.search_entry = ttk.Entry(self)
        self.search_entry.pack(fill='x', padx=10)
        self.search_entry.bind("<KeyRelease>", self.filter_gruppen)

    # Scrollbar und Canvas für Checkboxen
        #Hauptcontainer für linke Seite (Liste + Scrollbar)
        self.left_frame = ttk.Frame(self)
        self.left_frame.pack(side='left', fill='both', expand=True, padx=(10,5), pady=10)

        # Bps display in left_frame
        self.bps_label = ttk.Label(self.left_frame, text="Ausgewählte Menge: 0 B/s", font=('Arial', 10, 'bold'))
        self.bps_label.pack(fill='x', padx=10, pady=(0,10))

        # Canvas with scrollbar in left_frame
        self.canvas = tk.Canvas(self.left_frame, bg=self.cget('bg'), borderwidth=0, highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)

        self.scrollbar = ttk.Scrollbar(self.left_frame, orient='vertical', command=self.canvas.yview)
        self.scrollbar.pack(side='right', fill='y')

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')


    # Main container for right half (results display)
        self.right_frame = ttk.Frame(self)
        self.right_frame.pack(side='right', fill='both', expand=False, padx=(5,10), pady=10)

        # Frame for open file in upper half
        self.open_file_frame = ttk.Frame(self.right_frame)
        self.open_file_frame.pack(side='top', fill='x', pady=(0, 10))

        # Button zum Auswählen der einzulesenden Datei
        btn_open_file = ttk.Button(self.right_frame, text="Datei öffnen", command=self.datei_oeffnen_und_einlesen)
        btn_open_file.pack(fill='x', padx=10, pady=(0, 5))

        # Upper container for right half (Buttons)
        self.btn_frame = ttk.Frame(self.right_frame)
        self.btn_frame.pack(side='top', fill='x', pady=(0,10))

        # Button zum Anzeigen der ausgewählten Elemente
        self.btn_show = ttk.Button(self.btn_frame, text="Ausgewählte Gruppen anzeigen", command=self.show_selected_groups)
        self.btn_show.pack(side='left')

        # Export der ausgewählten Elemente als txt/lab Datei
        self.btn_export_lab = ttk.Button(self.btn_frame, text="Auswahl als LAB/TXT speichern", command=self.export_selected_to_lab_or_txt)
        self.btn_export_lab.pack(side='left', padx=5)

        # Button zum Auswählen bzw Abwählen aller Gruppen
        self.btn_alle_waehlen = ttk.Button(self.btn_frame, text="Alle auswählen/abwählen", command=self.toggle_alle_waehlen)
        self.btn_alle_waehlen.pack(side='left', padx= 10)
        
        # Export der ausgewählten Elemente als Excel Datei
        self.btn_export_excel = ttk.Button(self.btn_frame, text="Auswahl als Excel speichern", command=self.export_selected_to_excel)
        self.btn_export_excel.pack(side='left', padx=15)

        # Results display with scrollbar in right_frame
        self.result_text = tk.Text(self.right_frame, height=50, width=100)
        self.result_text.pack(side='left', fill='both', expand=True)
        self.result_text.configure(state='disabled')  # initial deaktiviert

        self.text_scrollbar = ttk.Scrollbar(self.right_frame, orient='vertical', command=self.result_text.yview)
        self.text_scrollbar.pack(side='right', fill='y')
        self.result_text.configure(yscrollcommand=self.text_scrollbar.set)

        self.erstelle_checkbuttons(original_daten)
        self.bind_mousewheel()


    def erstelle_checkbuttons(self, gruppen):
        # Berechne Bytes/s pro Gruppe
        haupt_bps, unter_bps = berechne_bytes_pro_sekunde(gruppen)

        self.hauptgruppen_accordions = {}
        self.untergruppen_vars = []
        self.check_vars = []


        # Alte Checkboxen entfernen
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Hauptgruppen sortieren nach Anzahl der Einträge (absteigend)
        sortierte_hauptgruppen = sorted(gruppen.items(), key=lambda x: sum(len(v) for v in x[1].values()), reverse=True)
        
        # Checkboxen für gruppierten Schlüssel
        for hauptgruppe, untergruppen in sortierte_hauptgruppen:
            # Text zeigt den Gruppennamen und Anzahl der Einträge
            bps_haupt = haupt_bps.get(hauptgruppe, 0)
            bps_haupt_formatiert = format_bytes_per_sec(bps_haupt)
            total_entries = sum(len(e) for e in untergruppen.values())

            untergruppen_bps = unter_bps.get(hauptgruppe, {})

            # Accordion mit Checkbox erstellen
            accordion = AccordionWithCheckbox(
                self.scrollable_frame,
                hauptgruppe=f"{hauptgruppe} ({total_entries} Einträge, {bps_haupt_formatiert})",
                untergruppen=untergruppen, untergruppen_bps = untergruppen_bps,
                on_selection_change = self.update_selected_bps
            )
            accordion.pack(fill='x', pady=5)

            # Hauptgruppen-Checkbox auf True setzen (ausgewählt)
            accordion.set_hauptgruppe_status(True)
            
            # Checkbox der Hauptgruppe speichern
            self.hauptgruppen_accordions[hauptgruppe] = accordion

            # Checkboxen der Untergruppen speichern
            for var, untergruppe, eintraege in accordion.subgroup_vars:
                self.untergruppen_vars.append((var, hauptgruppe, untergruppe, eintraege))
                self.check_vars.append((var, hauptgruppe, untergruppe, eintraege))

            # Auch Hauptgruppen Checkbox in check_vars speichern
            self.check_vars.append((accordion, hauptgruppe, '', []))
            self.update_selected_bps()


    def update_selected_bps(self):
        total_bps = 0.0
        for var, hauptgruppe, untergruppe, _ in self.untergruppen_vars:
            if var.get():
                accordion = self.hauptgruppen_accordions.get(hauptgruppe)
                if accordion:
                    bps_wert = accordion.untergruppen_bps.get(untergruppe, 0)
                    total_bps += bps_wert

        percent = (total_bps / MAX_BPS) * 100 if MAX_BPS > 0 else 0
        formated = format_bytes_per_sec(total_bps)
        max_formated = format_bytes_per_sec(MAX_BPS)

        text = f"Ausgewählte Menge: {formated} ({percent:.2f} % of {max_formated})"
        self.bps_label.config(text=text)

    def _on_mousewheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

    def bind_mousewheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)   # Windows, macOS
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)     # Linux scroll up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)     # Linux scroll down


    def datei_oeffnen_und_einlesen(self):
        dateipfad = filedialog.askopenfilename(
            title="Datei zum Einlesen auswählen",
            filetypes=[("LAB Dateien", "*.lab"), ("Text Dateien", "*.txt"), ("Alle Dateien", "*.*")]
        )
        if not dateipfad:
            return  # Wenn der Benutzer abbricht, nichts tun

        try:
            daten = lade_lab_datei_ab_start(dateipfad, start_marker="aaeps")
            gruppierte_daten = gruppiere_mit_untergruppen(daten)

            self.original_daten = gruppierte_daten
            anzeige_daten = gruppierte_daten
            self.erstelle_checkbuttons(anzeige_daten)

            self.result_text.configure(state='normal')
            self.result_text.delete(1.0, tk.END)
            self.result_text.configure(state='disabled')

            self.title(f"Filter Tool - Datei: {dateipfad}")
            # Speichere den aktuellen Dateipfad für den Exportvorschlag
            self.aktueller_dateipfad = dateipfad

        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Einlesen der Datei:\n{e}")


    def filter_gruppen(self, event=None):
        suchtext = self.such_entry.get().lower()
        if not suchtext:
            self.anzeige_daten = self.original_daten
        else:
            gefiltert = {}
            for hauptgruppe, untergruppen in self.original_daten.items():
                # Neue Untergruppen mit passenden Einträgen sammeln
                gefilterte_untergruppen = {}
                for untergruppe, eintraege in untergruppen.items():
                    # Prüfen, ob einer der Einträge den Suchtext enthält (in erster Spalte)
                    if any(suchtext in eintrag[0].lower() for eintrag in eintraege):
                        gefilterte_untergruppen[untergruppe] = eintraege
                        
                # Nur hinzufügen, wenn Untergruppen gefunden wurden
                if gefilterte_untergruppen:
                    gefiltert[hauptgruppe] = gefilterte_untergruppen
            
            self.anzeige_daten = gefiltert
        
        self.erstelle_checkbuttons(self.anzeige_daten)

    def toggle_alle_waehlen(self):
        # Prüfe, ob alle Hauptgruppen aktuell ausgewählt sind
        alle_ausgewaehlt = all(acc.get_hauptgruppe_status() for acc in self.hauptgruppen_accordions.values())

        neuer_status = not alle_ausgewaehlt  # Falls alle an, dann aus, sonst an

        # Setze alle Hauptgruppen
        for acc in self.hauptgruppen_accordions.values():
            acc.set_hauptgruppe_status(neuer_status)

        # Setze alle Untergruppen
        for var_unter, _, _, _ in self.untergruppen_vars:
            var_unter.set(neuer_status)

        self.update_selected_bps()


    def show_selected_groups(self):
        self.result_text.configure(state='normal')  # Schreibschutz vorübergehend aufheben
        self.result_text.delete(1.0, tk.END)

        for hauptgruppe, accordion in self.hauptgruppen_accordions.items():
            if accordion.get_hauptgruppe_status():
                self.result_text.insert(tk.END, f"Hauptgruppe: {hauptgruppe}\n")

                for var_unter, hg, ug, eintraege in self.untergruppen_vars:
                    if hg == hauptgruppe:
                        self.result_text.insert(tk.END, f"  Untergruppe: {ug if ug else '(keine)'}\n")

                        for eintrag in eintraege:
                            self.result_text.insert(tk.END, "    " + "; ".join(eintrag) + "\n")
                
                self.result_text.insert(tk.END, "\n")

        for var_unter, hg, ug, eintraege in self.untergruppen_vars:
            if var_unter.get() and not self.hauptgruppen_vars[hg].get():
                    uname = get_untergruppenname(hg, ug)

                    self.result_text.insert(tk.END, f"Hauptgruppe: {hg}\n")
                    self.result_text.insert(tk.END, f"  Untergruppe: {uname}\n")

                    for eintrag in eintraege:
                        self.result_text.insert(tk.END, "    " + "; ".join(eintrag) + "\n")
                    self.result_text.insert(tk.END, "\n")

        self.result_text.configure(state='disabled')  # Schreibschutz wieder aktivieren


    def export_selected_to_lab_or_txt(self):
        # Alle ausgewählten Einträge sammeln
        alle_ausgewaehlten = []

        for var, hauptgruppe, untergruppe, eintraege in self.check_vars:
            if var.get():
                alle_ausgewaehlten.extend(eintraege)
        
        if not alle_ausgewaehlten:
            messagebox.showwarning("Keine Auswahl", "Bitte wähle mindestens eine Gruppe zum Export aus.")
            return

        # Vorschlagsverzeichnis und Vorschlagsdateiname ermitteln
        initialdir = None
        initialfile = None
        if hasattr(self, 'aktueller_dateipfad'):
            initialdir = os.path.dirname(self.aktueller_dateipfad)
            initialfile = os.path.basename(self.aktueller_dateipfad)

        # Dateidialog zum Speichern öffnen
        dateipfad = filedialog.asksaveasfilename(
            defaultextension=".lab",
            filetypes=[("LAB Dateien", "*.lab"), ("Text Dateien", "*.txt"), ("Alle Dateien", "*.*")],
            title="Speichern als",
            initialdir=initialdir,
            initialfile=initialfile
        )
        
        if not dateipfad:
            return  # Benutzer hat abgebrochen

        try:
            with open(dateipfad, 'w', encoding='utf-8') as f:
                # Fester Header
                f.write("[SETTINGS]\n")
                f.write("Version;V1.1\n")
                f.write("MultirasterSeperator;&\n\n")
                f.write("[RAMCELL]\n")

                for eintrag in alle_ausgewaehlten:
                    zeile = ';'.join(eintrag)
                    f.write(zeile + '\n')
            messagebox.showinfo("Erfolg", f"Datei wurde erfolgreich gespeichert:\n{dateipfad}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern:\n{e}")


    def export_selected_to_excel(self):
        # Alle ausgewählten Einträge sammeln
        alle_ausgewaehlten = []

        for var, hauptgruppe, untergruppe, eintraege in self.check_vars:
            if var.get():
                alle_ausgewaehlten.extend(eintraege)

        if not alle_ausgewaehlten:
            messagebox.showwarning("Keine Auswahl", "Bitte wähle mindestens eine Gruppe zum Export aus.")
            return

        # Dateidialog zum Speichern öffnen
        dateipfad = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Dateien", "*.xlsx"), ("Alle Dateien", "*.*")],
            title="Speichern als")
        
        if not dateipfad:
            return  # Benutzer hat abgebrochen

        try:
            df = pd.DataFrame(alle_ausgewaehlten, columns=['Spalte1', 'Spalte2'])
            df.to_excel(dateipfad, index=False)
            messagebox.showinfo("Erfolg", f"Excel-Datei wurde erfolgreich exportiert nach:\n{dateipfad}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{e}")




if __name__ == "__main__":
    app = FilterTool()
    app.mainloop()