import io
import os
import datetime
import openai
from flask import Flask, request, render_template, redirect, url_for
from openai import OpenAI

app = Flask(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def call_gpt(messages, model="gpt-4o", temperature=0.0):
    """Call GPT with error handling"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        # Get form data
        verslag_type = request.form.get('verslag_type', 'TTE')
        
        # Handle file upload
        if 'audio_file' in request.files:
            audio_file = request.files['audio_file']
            if audio_file.filename != '':
                # Process audio file with Whisper
                if verslag_type == 'Anamnese':
                    prompt = "Dit is een conversatie tussen een arts en een patiënt in het West-Vlaams dialect. Transcribeer de volledige conversatie."
                else:
                    prompt = "Dit is een medische dictatie in het Nederlands van een cardioloog. Transcribeer de volledige dictatie."
                
                try:
                    # Convert FileStorage to the format expected by OpenAI
                    audio_file.seek(0)  # Reset file pointer to beginning
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=(audio_file.filename, audio_file.read(), audio_file.content_type),
                        prompt=prompt,
                        temperature=0.0
                    )
                    corrected_transcript = transcript.text
                except Exception as e:
                    return render_template('index.html', error=f"Transcriptie fout: {str(e)}")
            else:
                return render_template('index.html', error="⚠️ Geen bestand geselecteerd.")
        else:
            return render_template('index.html', error="⚠️ Geen bestand geselecteerd.")

        # Get today's date
        today = datetime.datetime.now().strftime("%d-%m-%Y")
        
        # Generate report based on type
        if verslag_type == 'TTE':
            template_instruction = f"""
BELANGRIJK: U krijgt een intuïtief dictaat van een cardioloog. Dit betekent dat de informatie:
- Niet in de juiste volgorde staat
- In informele bewoordingen kan zijn
- Correcties kan bevatten
- Heen en weer kan springen tussen onderwerpen

Uw taak: Analyseer het dictaat en vul het TTE-template in met de WERKELIJKE BEVINDINGEN.

KRITIEK: 
- VERVANG ALLE (...) met werkelijke gegevens uit het dictaat
- Als iets niet genoemd wordt, gebruik dan logische medische beschrijvingen
- GEEN (...) in de finale output - vul alles in met echte data
- Volg het template format EXACT regeltje per regeltje
- GEEN extra tekst voor of na het template
- GEEN "Verslag:" header - begin direct met "TTE op {today}:"

REGELS VOOR INVULLEN:
1. WERKELIJKE METINGEN: Gebruik exacte cijfers zoals gedicteerd (bijv. EDD 52 mm, LVEF 65%)
2. WERKELIJKE BESCHRIJVINGEN: Gebruik echte bevindingen (bijv. "eutroof", "gedilateerd", "prolaps")
3. LOGISCHE DEFAULTS: Als niet genoemd, gebruik medisch logische beschrijvingen:
   - Voor normale structuren: "eutroof", "normaal", "geen"
   - Voor functie: "goed", "normaal" 
   - Voor kleppen: "morfologisch normaal", "geen insufficiëntie"
4. GEEN (...) BEHOUDEN - vervang alles met echte gegevens

VOORBEELD INVULLING:
- Linker ventrikel: eutroof met EDD 52 mm, IVS 10 mm, PW 9 mm. Globale functie: goed met LVEF 65% geschat
- Mitralisklep: morfologisch prolaps. insufficiëntie: gering ; stenose: geen
- Atria: LA gedilateerd 45 mm, 65 mL, RA 35 mL

TEMPLATE STRUCTUUR (VUL IN MET ECHTE DATA):

TTE op {today}:
- Linker ventrikel: [vul in met echte data] met EDD [cijfer] mm, IVS [cijfer] mm, PW [cijfer] mm. Globale functie: [echte beoordeling] met LVEF [cijfer]% [methode]
- Regionaal: [echte bevinding]
- Rechter ventrikel: [echte data], globale functie: [echte beoordeling] met TAPSE [cijfer] mm en RV S' [cijfer] cm/s
- Diastole: [echte beoordeling] met E [cijfer] cm/s, A [cijfer] cm/s, E DT [cijfer] ms, E' septaal [cijfer] cm/s, E/E' [cijfer]. L-golf: [ja/neen]
- Atria: LA [echte beoordeling] [cijfer] mm, [cijfer] mL, RA [cijfer] mL
- Aortadimensies: sinus [cijfer] mm, sinotubulair [cijfer] mm, ascendens [cijfer] mm
- Mitralisklep: morfologisch [echte bevinding]. insufficiëntie: [echte graad] ; stenose: [echte bevinding]
- Aortaklep: [tricuspied/bicuspied], morfologisch [echte bevinding]. Functioneel: [echte bevinding]
- Pulmonalisklep: insufficiëntie: [echte graad] ; stenose: [echte bevinding]
- Tricuspiedklep: insufficiëntie: [echte graad] ; geschatte RVSP: [cijfer] mmHg + CVD [cijfer] mmHg gezien vena cava inferior: [cijfer] mm, variabiliteit: [echte bevinding]
- Pericard: [echte bevinding]

Recente biochemie op {today}:
- Hb [cijfer] g/dL
- Creatinine [cijfer] mg/dL en eGFR [cijfer] mL/min
- LDL [cijfer] mg/dL
- HbA1c [cijfer]%

Conclusie: [echte conclusie gebaseerd op bevindingen]

Beleid:
- Medicatie ongewijzigd/gewijzigd: [echte aanbeveling]
- Bijkomende investigaties: [echte aanbeveling]
- Controle over [cijfer] maand
"""
        else:
            # Default template for other types
            template_instruction = f"""
Maak een medisch verslag van het volgende dictaat:

{corrected_transcript}

Gebruik professionele medische terminologie en structuur.
"""

        # Generate structured report
        structured = call_gpt([
            {"role": "system", "content": template_instruction},
            {"role": "user", "content": corrected_transcript}
        ])
        
        # Clean the output to ensure only the template format is returned
        if "Verslag:" in structured:
            structured = structured.split("Verslag:")[-1].strip()
        
        # Remove any processing details that might appear before the template
        lines = structured.split('\n')
        template_start = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('TTE op') or line.strip().startswith('TEE op') or line.strip().startswith('Spoedconsult'):
                template_start = i
                break
        
        if template_start >= 0:
            structured = '\n'.join(lines[template_start:])

        return render_template('index.html', 
                             transcript=corrected_transcript,
                             structured=structured,
                             verslag_type=verslag_type)

    except Exception as e:
        return render_template('index.html', error=f"Er is een fout opgetreden: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

