import io
import os
import datetime
import requests
from flask import Flask, request, render_template

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"
GPT_URL = "https://api.openai.com/v1/chat/completions"

def call_gpt(messages, temperature=0.3):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o",
        "temperature": temperature,
        "messages": messages
    }
    response = requests.post(GPT_URL, headers=headers, json=data, timeout=90)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def detect_hallucination(text):
    """Detect Whisper hallucinations"""
    if not text or len(text.strip()) < 10:
        return True
    
    # Check for repetitive patterns
    words = text.lower().split()
    if len(words) > 10:
        # Check for excessive repetition
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # If any word appears more than 30% of the time, likely hallucination
        max_count = max(word_counts.values())
        if max_count > len(words) * 0.3:
            return True
    
    # Check for common hallucination phrases
    hallucination_phrases = [
        "deze film is gespecialiseerd",
        "geschiedenis van de oorlog",
        "dit is het gebouw",
        "west-vlaams en in het nederlands"
    ]
    
    text_lower = text.lower()
    for phrase in hallucination_phrases:
        if phrase in text_lower:
            return True
    
    return False

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    file = request.files.get('audio_file')
    verslag_type = request.form.get('verslag_type', 'consult')

    if not file or file.filename == '':
        return render_template('index.html', transcript='⚠️ Geen bestand geselecteerd.')

    # Prepare audio for Whisper
    audio_stream = io.BytesIO(file.read())
    files = {'file': (file.filename, audio_stream, file.content_type)}
    whisper_payload = {
        "model": "whisper-1", 
        "language": "nl", 
        "temperature": 0.0,
        "prompt": "Dit is een conversatie tussen een arts en een patiënt in het West-Vlaams dialect over cardiologische klachten en onderzoeken."
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    try:
        # 1) Whisper transcriptie
        resp = requests.post(WHISPER_URL, headers=headers, files=files, data=whisper_payload, timeout=120)
        resp.raise_for_status()
        raw_text = resp.json().get('text', '').strip()

        # Check for hallucination
        if detect_hallucination(raw_text):
            return render_template('index.html', transcript=f"""🚨 Whisper Hallucinatie Gedetecteerd

De audio-opname is waarschijnlijk te stil of onduidelijk voor betrouwbare transcriptie.

Transcriptie sample: "{raw_text[:200]}..."

Oplossingen:
1. Verhoog het volume van de audio met Audacity of GarageBand
2. Neem opnieuw op met microfoon dichter bij de sprekers
3. Splits lange opnames in kortere segmenten
4. Pauzeer tijdens stille procedures (echo, ECG)

Probeer opnieuw met verbeterde audio.""")

        # 2) Corrigeer transcriptie in medisch Nederlands
        corrected = call_gpt([
            {"role": "system", "content": "Corrigeer deze transcriptie in correct medisch Nederlands. Behoud alle genoemde cijfers en metingen exact."},
            {"role": "user",   "content": raw_text}
        ])

        # Determine today's date
        today = datetime.date.today().strftime('%d-%m-%Y')

        # 3) Kies juiste template
        if verslag_type == 'TTE':
            template_instruction = f"""
Gebruik uitsluitend onderstaand TTE-verslagformat. Vul alleen velden in die expliciet genoemd zijn. Vermijd incomplete zinnen. Indien waarden niet vermeld zijn, laat ze weg en herschrijf de zin grammaticaal correct. Beschrijf structuren als 'normaal' indien niet besproken. GEEN voorgeschiedenis, context of advies:

TTE op {today}:
- Linker ventrikel: (...)troof met EDD (...) mm, IVS (...) mm, PW (...) mm. Globale functie: (goed/licht gedaald/matig gedaald/ernstig gedaald) met LVEF (...)% (geschat/monoplane/biplane).
- Regionaal: (geen kinetiekstoornissen/zone van hypokinesie/zone van akinesie)
- Rechter ventrikel: (...)troof, globale functie: (...) met TAPSE (...) mm en RV S' (...) cm/s
- Diastole: (normaal/vertraagde relaxatie/dysfunctie graad 2/dysfunctie graad 3) met E (...) cm/s, A (...) cm/s, E DT (...) ms, E' septaal (...) cm/s, E/E' (...). L-golf: (ja/neen).
- Atria: LA (normaal/licht gedilateerd/sterk gedilateerd) (...) mm, (...) mL, RA (...) mL
- Aortadimensies: sinus (...) mm, sinotubulair (...) mm, ascendens (...) mm
- Mitralisklep: morfologisch (normaal/sclerotisch/verdikt/prolaps/restrictief). insufficiëntie: (...), stenose: geen.
- Aortaklep: (tricuspied/bicuspied), morfologisch (normaal/sclerotisch/mild verkalkt/matig verkalkt/ernstig verkalkt). Functioneel: insufficiëntie: geen, stenose: geen.
- Pulmonalisklep: insufficiëntie: (...), stenose: geen.
- Tricuspiedklep: insufficiëntie: (...), geschatte RVSP: (...) mmHg of niet opmeetbaar + CVD (...) mmHg gezien vena cava inferior: (...) mm, variabiliteit: (...).
- Pericard: (...).

Recente biochemie op {today}:
- Hb (...) g/dL
- Creatinine (...) mg/dL en eGFR (...) mL/min
- LDL (...) mg/dL
- HbA1c (...)%

Conclusie:
(...)

Beleid:
- Medicatie ongewijzigd/gewijzigd: (...)
- Bijkomende investigaties: (...)
- Controle over (...) maand
"""
        elif verslag_type == 'TEE':
            template_instruction = f"""
Gebruik uitsluitend onderstaand TEE-verslagformat. Vul alleen expliciet genoemde zaken in. Laat velden weg indien niet vermeld en herschrijf zinnen grammaticaal correct. Gebruik defaults enkel voor structuren die niet besproken zijn. GEEN voorgeschiedenis of advies:

Onderzoeksdatum: {today}
Bevindingen: TEE ONDERZOEK : 3D TEE met (Philips/GE) toestel
Indicatie: (...)
Afname mondeling consent: dr. Verbeke. Informed consent: patiënt kreeg uitleg over aard onderzoek, mogelijke resultaten en procedurele risico's en verklaart zich hiermee akkoord.
Supervisie: dr (...)
Verpleegkundige: (...)
Anesthesist: dr. (...)
Locatie: endoscopie 3B
Sedatie met (Midazolam/Propofol) en topicale Xylocaine spray.
(Vlotte/moeizame) introductie TEE probe, (Vlot/moeizaam) verloop van onderzoek zonder complicatie.

VERSLAG:
- Linker ventrikel is (...), (niet/mild/matig/ernstig) gedilateerd en (...) contractiel (zonder/met) regionale wandbewegingstoornissen.
- Rechter ventrikel is (...), (...) gedilateerd en (...) contractiel.
- Atria zijn (...) gedilateerd.
- Linker hartoortje is (...), (geen/beperkt) spontaan contrast, zonder toegevoegde structuur. Snelheden: (...) cm/s.
- Interatriaal septum: (...)
- Mitralisklep: (...), insufficiëntie: (...), stenose: (...).
- Aortaklep: (...), insufficiëntie: (...), stenose: (...).
- Tricuspiedklep: (...), insufficiëntie: (...).
- Pulmonalisklep: (...).
- Aorta ascendens: (...).
- Pulmonale arterie: (...).
- VCI/levervenes: (...).
- Pericard: (...).
"""
        elif verslag_type == 'spoedconsult':
            template_instruction = f"""
Schrijf een spoedconsult verslag in **exacte** volgende structuur.
Vervang alleen zinnen **zonder** cijfers door grammaticaal correcte tekst, laat alle andere zinnen onaangeroerd:

Spoedconsult cardiologie op {today}

Reden van komst: (exacte tekst uit transcriptie)

Anamnese:
Thoracale last ja/neen: welk soort pijn (scheurend, druk, messteken), uitstraling, hoe lang, beïnvloeding door ademhaling etc
Syncope ja/neen: prodromi? Tijdens inspanning? RSP of palpitaties net voordien?
Palpitaties ja/neen: wanneer, hoe lang, graduele/sudden onset, regelmatig/onregelmatig,…
Dyspneu ja/neen: wanneer, hoe erg (NYHA), sinds wanneer,…

Klinisch onderzoek:
Cor: regelmatig, geen souffle.
Longen zuiver.
Perifeer: geen oedemen.
Jugulairen niet gestuwd.

Aanvullend onderzoek:
ECG op {today}:
- ritme: (sinusaal/VKF/voorkamerflutter/atriale tachycardie) met ventriculair antwoord aan (...)/min.
- PR: (normaal/verlengd/verkort) (...) ms
- QRS: (normale/linkser/rechter) as, (smal/verbreed met LBTB/verbreed met RBTB/verbreed met aspecifiek IVCD)
- repolarisatie: (normaal/gestoord met …)
- QTc: (normaal/verlengd) (…) ms

Conclusie:

Beleid:
- Medicatie: (...)
- Bijkomende investigaties: (...)
- Opvolging: (...)

Laat secties weg indien **geen** data; herschrijf alleen zinnen zonder cijfers; behoud alle numerieke data ongewijzigd
"""
        else:  # raadpleging or consult
            template_instruction = f"""
Schrijf een medisch verslag in **exacte** volgende structuur.
Vervang alleen zinnen **zonder** cijfers door grammaticaal correcte tekst, laat alle andere zinnen onaangeroerd:

Antecedenten
Persoonlijke antecedenten:
- ziekenhuisopnames
- operaties
Familiaal:
- kinderen? gezond?
- prematuur coronair lijden?
- plotse dood?
Beroep:
Usus:
- nicotine?
- ethyl?
- druggebruik?
Reden van komst: (exacte tekst uit transcriptie)

Anamnese:
Thoracale last ja/neen: welk soort pijn (scheurend, druk, messteken), uitstraling, hoe lang, beïnvloeding door ademhaling etc
Syncope ja/neen: prodromi? Tijdens inspanning? RSP of palpitaties net voordien?
Palpitaties ja/neen: wanneer, hoe lang, graduele/sudden onset, regelmatig/onregelmatig,…
Dyspneu ja/neen: wanneer, hoe erg (NYHA), sinds wanneer,…
Zwelling benen ja/neen: sinds wanneer, hoeveel kg bijgekomen in gewicht,…

Klinisch onderzoek:
Cor: regelmatig, geen souffle.
Longen zuiver.
Perifeer: geen oedemen.
Jugulairen niet gestuwd.

Aanvullend onderzoek:
ECG op {today}:
- ritme: (sinusaal/VKF/voorkamerflutter/atriale tachycardie) met ventriculair antwoord aan (...)/min.
- PR: (normaal/verlengd/verkort) (...) ms
- QRS: (normale/linkser/rechter) as, (smal/verbreed met LBTB/verbreed met RBTB/verbreed met aspecifiek IVCD)
- repolarisatie: (normaal/gestoord met …)
- QTc: (normaal/verlengd) (…) ms

Fietsproef op {today}:
- Patiënt fietst tot (…) W waarbij de hartslag oploopt van (…) tot (…) /min ((…)% van voorspelde waarde)
- Bloeddruk stijgt tot (…) / (…) mmHg
- Klachten: (ja/neen)
- ECG tijdens inspanning toont (wel/geen) argumenten voor ischemie en (wel/geen) aritmie

TTE op {today}:
- Linker ventrikel: (...)troof met EDD (...) mm, IVS (...) mm, PW (...) mm. Globale functie: (goed/licht gedaald/matig gedaald/ernstig gedaald) met LVEF (...)% (geschat/monoplane/biplane)
- Regionaal: (geen kinetiekstoornissen/zone van hypokinesie/zone van akinesie)
- Rechter ventrikel: (...)troof, globale functie: (...) met TAPSE (...) mm en RV S' (...) cm/s
- Diastole: (normaal/vertraagde relaxatie/dysfunctie graad 2/dysfunctie graad 3) met E (...) cm/s, A (...) cm/s, E DT (...) ms, E' septaal (...) cm/s, E/E' (…). L-golf: (ja/neen)
- Atria: LA (normaal/licht gedilateerd/sterk gedilateerd) (...) mm, (…) mL, RA (…) mL
- Aortadimensies: sinus (…) mm, sinotubulair (…) mm, ascendens (…) mm
- Mitralisklep: morfologisch (normaal/sclerotisch/verdikt/prolaps/restrictief). insufficiëntie: (…) ; stenose: geen
- Aortaklep: (tricuspied/bicuspied), morfologisch (normaal/sclerotisch/mild verkalkt/matig verkalkt/ernstig verkalkt). Functioneel: geen tekort
- Pulmonalisklep: insufficiëntie: (…) ; stenose: geen
- Tricuspiedklep: insufficiëntie: (…) ; geschatte RVSP: (…) mmHg of niet opmeetbaar + CVD (…) mmHg gezien vena cava inferior: (…) mm, variabiliteit: (…) 
- Pericard: (…)  

Recente biochemie op {today}:
- Hb (…) g/dL
- Creatinine (…) mg/dL en eGFR (…) mL/min
- LDL (…) mg/dL
- HbA1c (…)%

Conclusie:

Beleid:
- Medicatie ongewijzigd/gewijzigd: …
- Bijkomende investigaties: …
- Controle over … maand

Laat secties weg indien **geen** data; herschrijf alleen zinnen zonder cijfers; behoud alle numerieke data ongewijzigd
"""
        
        # 4) Genereer verslag
        structured = call_gpt([
            {"role": "system",  "content": template_instruction},
            {"role": "user",    "content": corrected}
        ])

        # 5) Validatie op onnauwkeurigheden
        validation = call_gpt([
            {"role": "system", "content": (
                "Controleer het verslag: verwijder niet in transcriptie vermelde data en corrigeer inconsistenties. "
                "Behoud alle genoemde cijfers en metingen exact zoals vermeld."
            )},
            {"role": "user",   "content": f"Transcriptie:\n{corrected}\n\nVerslag:\n{structured}"}
        ])

        # 6) ESC/AHA-advies
        advice = ""
        if verslag_type in ['consult', 'raadpleging', 'spoedconsult']:
            advice = call_gpt([
                {"role": "system", "content": (
                    "Geef concrete, evidence-based aanbevelingen inclusief doseringen, Class/LoE en links."
                )},
                {"role": "user", "content": validation}
            ])

        # 7) Render output
        if verslag_type in ['TTE', 'TEE']:
            return render_template('index.html', transcript=validation)
        return render_template('index.html', transcript=validation, advies=advice)

    except Exception as e:
        return render_template('index.html', transcript=f"⚠️ Fout: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

