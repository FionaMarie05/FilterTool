import tkinter as tk
from tkinter import ttk
#import pandas as pd
from collections import defaultdict
from tkinter import filedialog, messagebox
import os
import re



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

    def __init__(self, master, hauptgruppe, untergruppen, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
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
        self.var_haupt = tk.BooleanVar()
        self.checkbox = tk.Checkbutton(header_frame, text=hauptgruppe, variable=self.var_haupt, font=('Arial', 10, 'bold'), 
                                       command=self.on_hauptgruppe_toggle)
        self.checkbox.pack(side='left', padx=5)

        # Frame für Untergruppen, zunächst versteckt
        self.content_frame = tk.Frame(self)
        self.content_frame.pack(fill='x', expand=True)
        self.content_frame.pack_forget()

        # Untergruppen-Checkboxen
        self.subgroup_vars = []
        for untergruppe, eintraege in sorted(untergruppen.items(), key=lambda x: len(x[1]), reverse=True):
            var = tk.BooleanVar(value=True)
            uname = untergruppe if untergruppe else "(keine Untergruppe)"
            cb_text = f"{uname} ({len(eintraege)} Einträge)"
            cb = tk.Checkbutton(self.content_frame, text=cb_text, variable=var, command=self.on_untergruppe_toggle)
            cb.pack(anchor='w', padx=20)
            self.subgroup_vars.append((var, untergruppe, eintraege))


    def toggle(self):
        if self.is_expanded:
            self.content_frame.pack_forget()
            self.toggle_button.config(text="v")
            self.is_expanded = False
        else:
            self.content_frame.pack(fill='x', expand=True)
            self.toggle_button.config(text="^")
            self.is_expanded = True


    def on_hauptgruppe_toggle(self):
        neuer_status = self.var_haupt.get()
        # Alle Untergruppen-Checkboxen entsprechend setzen
        for var, _, _ in self.subgroup_vars:
            var.set(neuer_status)

    def on_untergruppe_toggle(self):
        # Wenn alle Untergruppen ausgewählt sind, Hauptgruppe auswählen, sonst abwählen
        alle_ausgewaehlt = all(var.get() for var, _, _ in self.subgroup_vars)
        self.var_haupt.set(alle_ausgewaehlt)




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
        self.such_label = ttk.Label(self, text="Gruppen suchen:")
        self.such_label.pack(pady=(10,0))
        
        self.such_entry = ttk.Entry(self)
        self.such_entry.pack(fill='x', padx=10)
        self.such_entry.bind("<KeyRelease>", self.filter_gruppen)

        # Scrollbar und Canvas für Checkboxen
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True, padx=(10,0), pady=10)
        self.scrollbar.pack(side="right", fill="y", pady=10)

        # Button zum Auswählen der einzulesenden Datei
        btn_datei_frame = ttk.Frame(self)
        btn_datei_frame.pack(fill='x', padx=10, pady=(10, 5))
        btn_datei_oeffnen = ttk.Button(btn_datei_frame, text="Datei öffnen", command=self.datei_oeffnen_und_einlesen)
        btn_datei_oeffnen.pack(fill='x', padx=10, pady=(10, 5))

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', padx=10, pady=(0,10))

        # Button zum Anzeigen der ausgewählten Elemente
        self.btn_show = ttk.Button(btn_frame, text="Ausgewählte Gruppen anzeigen", command=self.show_selected_groups)
        self.btn_show.pack(side='left')

        # Export der ausgewählten Elemente als txt/lab Datei
        self.btn_export_lab = ttk.Button(btn_frame, text="Auswahl als LAB/TXT speichern", command=self.export_selected_to_lab_or_txt)
        self.btn_export_lab.pack(side='left', padx=5)

        # Button zum Auswählen bzw Abwählen aller Gruppen
        self.btn_alle_waehlen = ttk.Button(btn_frame, text="Alle auswählen/abwählen", command=self.toggle_alle_waehlen)
        self.btn_alle_waehlen.pack(side='left', padx= 10)
        
        # Export der ausgewählten Elemente als Excel Datei
        #self.btn_export_excel = ttk.Button(btn_frame, text="Auswahl als Excel speichern", command=export_selected_to_excel)
        #self.btn_export_excel.pack(side='left', padx=15)

        # Textfeld zur Anzeige der Ergebnisse
        self.result_text = tk.Text(self, height=50, width=100)
        self.result_text.pack(padx=10, pady=(0,10))
        self.result_text.configure(state='disabled')    # Textfeld initial auf "disabled" setzen

        self.erstelle_checkbuttons(original_daten)


    def erstelle_checkbuttons(self, gruppen):
        # Berechne Bytes/s pro Gruppe
        haupt_bps, unter_bps = berechne_bytes_pro_sekunde(gruppen)

        self.hauptgruppen_vars = {}
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

            # Accordion mit Checkbox erstellen
            accordion = AccordionWithCheckbox(
                self.scrollable_frame,
                hauptgruppe=f"{hauptgruppe} ({total_entries} Einträge, {bps_haupt_formatiert})",
                untergruppen=untergruppen
            )
            accordion.pack(fill='x', pady=5)

            # Hauptgruppen-Checkbox auf True setzen (ausgewählt)
            accordion.var_haupt.set(True)
            
            # Checkbox der Hauptgruppe speichern
            self.hauptgruppen_vars[hauptgruppe] = accordion.var_haupt

            # Checkboxen der Untergruppen speichern
            for var, untergruppe, eintraege in accordion.subgroup_vars:
                self.untergruppen_vars.append((var, hauptgruppe, untergruppe, eintraege))
                self.check_vars.append((var, hauptgruppe, untergruppe, eintraege))

            # Auch Hauptgruppen Checkbox in check_vars speichern
            self.check_vars.append((accordion.var_haupt, hauptgruppe, '', []))


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
        alle_ausgewaehlt = all(var.get() for var in self.hauptgruppen_vars.values())

        neuer_status = not alle_ausgewaehlt  # Falls alle an, dann aus, sonst an

        # Setze alle Hauptgruppen
        for var_haupt in self.hauptgruppen_vars.values():
            var_haupt.set(neuer_status)

        # Setze alle Untergruppen
        for var_unter, _, _, _ in self.untergruppen_vars:
            var_unter.set(neuer_status)


    def show_selected_groups(self):
        self.result_text.configure(state='normal')  # Schreibschutz vorübergehend aufheben
        self.result_text.delete(1.0, tk.END)

        for hauptgruppe, var_haupt in self.hauptgruppen_vars.items():
            if var_haupt.get():
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
        #
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
                for eintrag in alle_ausgewaehlten:
                    zeile = ';'.join(eintrag)
                    f.write(zeile + '\n')
            messagebox.showinfo("Erfolg", f"Datei wurde erfolgreich gespeichert:\n{dateipfad}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern:\n{e}")


   #def export_selected_to_excel(self):
        # Alle ausgewählten Einträge sammeln
#       alle_ausgewaehlten = []

#       for var, hauptgruppe, untergruppe, eintraege in self.check_vars:
#           if var.get():
#               alle_ausgewaehlten.extend(eintraege)

        # Dateidialog zum Speichern öffnen
#       dateipfad = filedialog.asksaveasfilename(
#       defaultextension=".xlsx",
#       filetypes=[("Excel Dateien", "*.xlsx"), ("Alle Dateien", "*.*")],
#       title="Speichern als")
        
#       if not dateipfad:
#            return  # Benutzer hat abgebrochen

        # Dataframe erstellen
#       try:
#           df = pd.DataFrame(alle_ausgewaehlten, columns=['Spalte1', 'Spalte2'])
#           df.to_excel(dateipfad, index=False)
#           messagebox.showinfo("Erfolg", f"Excel-Datei wurde erfolgreich exportiert nach:\n{dateipfad}")
#       except Exception as e:
#           messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{e}")




if __name__ == "__main__":
    app = FilterTool()
    app.mainloop()