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

def quality_control_review(structured_report, original_transcript):
    """Perform quality control review of the structured report"""
    
    review_instruction = """
Je bent een ervaren cardioloog die een tweede review doet van een TTE-verslag. 
Controleer het verslag op de volgende punten:

CORRECTE MEDISCHE NEDERLANDSE TERMINOLOGIE (PRIORITEIT!):
- Corrigeer ALLE incorrecte samengestelde woorden:
  ❌ 'pulmonaardruk' → ✅ 'pulmonale druk'
  ❌ 'posteriorklepplat' → ✅ 'posterieur mitraalklepblad'
  ❌ 'tricuspiedklep' → ✅ 'tricuspidalisklep'
  ❌ 'mitraalsklep' → ✅ 'mitralisklep'
  ❌ 'aortaklep' → ✅ 'aortaklep'
- Gebruik ALTIJD correcte medische Nederlandse terminologie

MEDISCHE CONSISTENTIE:
- Zijn de metingen medisch logisch? (bijv. LVEF vs functie beschrijving)
- Zijn er tegenstrijdigheden tussen verschillende secties?
- Kloppen de verhoudingen tussen verschillende parameters?

TEMPLATE VOLLEDIGHEID:
- Zijn alle verplichte secties aanwezig?
- Is de formatting correct en consistent?
- Zijn er lege velden die ingevuld zouden moeten zijn?

LOGISCHE COHERENTIE:
- Klopt de conclusie met de bevindingen?
- Is het beleid logisch gebaseerd op de bevindingen?
- Zijn er missing links tussen bevindingen en conclusies?

MEDISCHE VEILIGHEID:
- Zijn er potentieel gevaarlijke inconsistenties?
- Zijn kritieke bevindingen correct weergegeven?
- Is de terminologie correct gebruikt?

Als je fouten of inconsistenties vindt, corrigeer ze en geef het verbeterde verslag terug.
Als alles correct is, geef het originele verslag terug zonder wijzigingen.

BELANGRIJK: 
- Behoud de exacte template structuur
- Voeg GEEN nieuwe medische gegevens toe die niet in het origineel stonden
- Corrigeer alleen echte fouten en inconsistenties
- CORRIGEER ALTIJD incorrecte terminologie naar correcte medische Nederlandse termen
- Geef ALLEEN het gecorrigeerde verslag terug, geen uitleg

Origineel dictaat voor referentie:
{original_transcript}

Te reviewen verslag:
{structured_report}

Gecorrigeerd verslag:
"""
    
    try:
        reviewed_report = call_gpt([
            {"role": "system", "content": review_instruction.format(
                original_transcript=original_transcript,
                structured_report=structured_report
            )},
            {"role": "user", "content": "Voer de quality control review uit."}
        ])
        
        return reviewed_report.strip()
    except Exception as e:
        # If review fails, return original report
        return structured_report

def detect_hallucination(structured_report, transcript):
    """Detect potential hallucination in the structured report"""
    
    import re
    
    # Extract numbers from the structured report and transcript
    numbers_in_report = re.findall(r'\d+(?:\.\d+)?', structured_report)
    numbers_in_transcript = re.findall(r'\d+(?:\.\d+)?', transcript)
    
    # Convert to sets for better comparison
    report_numbers = set(numbers_in_report)
    transcript_numbers = set(numbers_in_transcript)
    
    # Count fabricated numbers (in report but not in transcript)
    fabricated_numbers = len(report_numbers - transcript_numbers)
    total_numbers = len(report_numbers)
    
    # More sophisticated hallucination detection
    if total_numbers > 0:
        fabrication_ratio = fabricated_numbers / total_numbers
        
        # Only flag as hallucination if:
        # 1. High fabrication ratio (>70%) AND significant number of fabricated numbers (>5)
        # 2. OR extremely high fabrication ratio (>90%) with any fabricated numbers
        if (fabrication_ratio > 0.7 and fabricated_numbers > 5) or (fabrication_ratio > 0.9 and fabricated_numbers > 2):
            return True, f"Mogelijk hallucinatie gedetecteerd: {fabricated_numbers}/{total_numbers} cijfers niet in origineel dictaat (ratio: {fabrication_ratio:.1%})"
    
    # Check for suspiciously repetitive patterns (classic hallucination sign)
    lines = structured_report.split('\n')
    repetitive_patterns = 0
    for line in lines:
        # Look for repetitive phrases or identical measurements across different structures
        if 'normaal' in line.lower() and len(re.findall(r'normaal', line.lower())) > 2:
            repetitive_patterns += 1
    
    if repetitive_patterns > 5:
        return True, "Mogelijk hallucinatie: verdacht repetitieve patronen gedetecteerd"
    
    # Check for impossible medical combinations
    if "LVEF 65%" in structured_report and "ernstig gedaalde functie" in structured_report:
        return True, "Mogelijk hallucinatie: tegenstrijdige medische bevindingen"
    
    # If transcript is very short but report is very detailed, might be hallucination
    transcript_words = len(transcript.split())
    report_words = len(structured_report.split())
    
    if transcript_words < 20 and report_words > 200 and total_numbers > 10:
        return True, f"Mogelijk hallucinatie: zeer kort dictaat ({transcript_words} woorden) maar uitgebreid verslag ({report_words} woorden)"
    
    return False, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        # Get form data
        verslag_type = request.form.get('verslag_type', 'TTE')
        disable_hallucination = request.form.get('disable_hallucination_detection') == 'true'
        
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

KRITIEKE VEILIGHEIDSREGEL: VERZIN GEEN MEDISCHE GEGEVENS!

CORRECTE MEDISCHE NEDERLANDSE TERMINOLOGIE:
- Gebruik ALTIJD correcte medische Nederlandse termen
- GEEN samengestelde woorden zoals 'pulmonaardruk' → gebruik 'pulmonale druk'
- GEEN 'posteriorklepplat' → gebruik 'posterieur mitraalklepblad'
- GEEN 'tricuspiedklep' → gebruik 'tricuspidalisklep'
- GEEN 'mitraalsklep' → gebruik 'mitralisklep'
- GEEN 'aortaklep' → gebruik 'aortaklep'

CORRECTE TERMINOLOGIE VOORBEELDEN:
❌ FOUT: pulmonaardruk, posteriorklepplat, tricuspiedklep
✅ CORRECT: pulmonale druk, posterieur mitraalklepblad, tricuspidalisklep

Uw taak: Analyseer het dictaat en vul het TTE-template in met ALLEEN de WERKELIJK GENOEMDE BEVINDINGEN.

TEMPLATE STRUCTUUR REGELS:
- BEHOUD ALLE TEMPLATE LIJNEN - laat geen enkele regel weg
- Voor elke lijn: geef een medische beschrijving gebaseerd op wat genoemd is
- Voor specifieke parameters (cijfers): alleen invullen als expliciet genoemd
- Voor algemene beschrijvingen: gebruik logische medische termen
- GEBRUIK ALTIJD CORRECTE MEDISCHE NEDERLANDSE TERMINOLOGIE

INVUL REGELS:
1. EXPLICIET GENOEMDE AFWIJKINGEN: Vul exact in zoals gedicteerd MAAR met correcte terminologie
2. NIET GENOEMDE STRUCTUREN: Gebruik "normaal" of "eutroof" 
3. SPECIFIEKE CIJFERS: Alleen als letterlijk genoemd (EDD, LVEF, etc.)
4. ALGEMENE FUNCTIE: Afleiden uit context ("normale echo" = goede functie)
5. TERMINOLOGIE: Altijd correcte medische Nederlandse termen gebruiken

VOORBEELDEN VAN CORRECTE INVULLING:

Als "normale echo behalve..." gedicteerd:
- Linker ventrikel: eutroof, globale functie goed
- Regionaal: geen kinetiekstoornissen  
- Rechter ventrikel: normaal, globale functie goed

Als specifieke afwijking genoemd:
- Mitralisklep: morfologisch prolaps. insufficiëntie: spoortje
- Atria: LA licht vergroot 51 mm

Als niets specifiek genoemd:
- Aortaklep: tricuspied, morfologisch normaal. Functioneel: normaal
- Pericard: normaal

VOLLEDIGE TEMPLATE STRUCTUUR:

TTE op {today}:
- Linker ventrikel: [normaal/eutroof als niet anders vermeld, specifieke afwijkingen als genoemd]
- Regionaal: [geen kinetiekstoornissen als niet anders vermeld]
- Rechter ventrikel: [normaal als niet anders vermeld, specifieke afwijkingen als genoemd]
- Diastole: [normaal als niet anders vermeld, specifieke bevindingen als genoemd]
- Atria: [normaal als niet anders vermeld, specifieke afwijkingen als genoemd]
- Aortadimensies: [normaal als niet anders vermeld, specifieke metingen als genoemd]
- Mitralisklep: [morfologisch normaal als niet anders vermeld, specifieke afwijkingen als genoemd]
- Aortaklep: [tricuspied, morfologisch normaal als niet anders vermeld]
- Pulmonalisklep: [normaal als niet anders vermeld, specifieke afwijkingen als genoemd]
- Tricuspidalisklep: [normaal als niet anders vermeld, specifieke afwijkingen als genoemd]
- Pericard: [normaal als niet anders vermeld]

Recente biochemie op {today}:
[Alleen invullen als biochemie expliciet genoemd in dictaat]

Conclusie: [Samenvatting van werkelijk genoemde afwijkingen]

Beleid:
[Alleen invullen als expliciet genoemd in dictaat]

VEILIGHEIDSCHECK: Elk cijfer moet ECHT in het dictaat staan!
TERMINOLOGIE CHECK: Gebruik ALLEEN correcte medische Nederlandse termen!
"""
        elif verslag_type == 'TEE':
            template_instruction = f"""
BELANGRIJK: U krijgt een intuïtief dictaat van een TEE (transesofageale echocardiografie). Dit betekent dat de informatie:
- Niet in de juiste volgorde staat
- In informele bewoordingen kan zijn
- Correcties kan bevatten
- Heen en weer kan springen tussen onderwerpen

KRITIEKE VEILIGHEIDSREGEL: VERZIN GEEN MEDISCHE GEGEVENS!

CORRECTE MEDISCHE NEDERLANDSE TERMINOLOGIE:
- Gebruik ALTIJD correcte medische Nederlandse termen
- GEEN samengestelde woorden
- Correcte anatomische benamingen voor TEE structuren

Uw taak: Analyseer het dictaat en vul het TEE-template in met ALLEEN de WERKELIJK GENOEMDE BEVINDINGEN.

TEMPLATE STRUCTUUR REGELS:
- BEHOUD ALLE TEMPLATE LIJNEN - laat geen enkele regel weg
- Voor elke lijn: geef een medische beschrijving gebaseerd op wat genoemd is
- Voor specifieke parameters (cijfers): alleen invullen als expliciet genoemd
- Voor algemene beschrijvingen: gebruik logische medische termen
- GEBRUIK ALTIJD CORRECTE MEDISCHE NEDERLANDSE TERMINOLOGIE

INVUL REGELS:
1. EXPLICIET GENOEMDE AFWIJKINGEN: Vul exact in zoals gedicteerd MAAR met correcte terminologie
2. NIET GENOEMDE STRUCTUREN: Gebruik "normaal" of "geen afwijkingen"
3. SPECIFIEKE CIJFERS: Alleen als letterlijk genoemd
4. ALGEMENE FUNCTIE: Afleiden uit context
5. TERMINOLOGIE: Altijd correcte medische Nederlandse termen gebruiken

VOLLEDIGE TEE TEMPLATE STRUCTUUR:

Onderzoeksdatum: {today}
Bevindingen: TEE ONDERZOEK : 3D TEE met [toestel als genoemd, anders "niet vermeld"] toestel
Indicatie: [alleen invullen als expliciet genoemd in dictaat]
Afname mondeling consent: dr. Verbeke. Informed consent: patiënt kreeg uitleg over aard onderzoek, mogelijke resultaten en procedurele risico's en verklaart zich hiermee akkoord.
Supervisie: dr [alleen invullen als genoemd]
Verpleegkundige: [alleen invullen als genoemd]
Anesthesist: dr. [alleen invullen als genoemd]
Locatie: [alleen invullen als genoemd]
Sedatie met [alleen invullen als genoemd] en topicale Xylocaine spray.
[Vlotte/moeizame] introductie TEE probe, [Vlot/moeizaam] verloop van onderzoek zonder complicatie.

VERSLAG:
- Linker ventrikel is [eutroof/hypertroof als genoemd], [niet/mild/matig/ernstig] gedilateerd en [normocontractiel/licht hypocontractiel/matig hypocontractiel/ernstig hypocontractiel] [zonder/met] regionale wandbewegingstoornissen.
- Rechter ventrikel is [eutroof/hypertroof als genoemd], [niet/mild/matig/ernstig] gedilateerd en [normocontractiel/licht hypocontractiel/matig hypocontractiel/ernstig hypocontractiel].
- De atria zijn [niet/licht/matig/sterk] gedilateerd.
- Linker hartoortje is [niet/wel] vergroot, er is [geen/beperkt] spontaan contrast, zonder toegevoegde structuur. Hartoortje snelheden [alleen cijfer als genoemd] cm/s.
- Interatriaal septum [is intact met kleurendoppler en na contrasttoediening met Valsalva manoever/is intact met kleurendoppler maar zonder contrast/vertoont een PFO/vertoont een ASD].
- Mitralisklep: [natieve klep/bioprothese/mechanische kunstklep], morfologisch [normaal/degeneratief/prolaps], er is [geen/lichte/matige/ernstige] insufficiëntie, er is [geen/lichte/matige/ernstige] stenose, [zonder/met] toegevoegde structuur.
* Mitraalinsufficientie vena contracta [alleen als genoemd] mm, ERO [alleen als genoemd] mm2 en RVol [alleen als genoemd] ml/slag.
- Aortaklep: [natieve klep/bioprothese/mechanische kunstklep], morfologisch [normaal/degeneratief/prolaps], [niet/mild/matig/ernstig] verkalkt, er is [geen/lichte/matige/ernstige] insufficiëntie, er is [geen/lichte/matige/ernstige] stenose [zonder/met] toegevoegde structuur.
Dimensies: LVOT [alleen als genoemd] mm, aorta sinus [alleen als genoemd] mm, sinutubulaire junctie [alleen als genoemd] mm, aorta ascendens boven de sinutubulaire junctie [alleen als genoemd] mm.
* Aortaklepinsufficientie vena contracta [alleen als genoemd] mm, ERO [alleen als genoemd] mm2 en RVol [alleen als genoemd] ml/slag.
* Aortaklepstenose piekgradient [alleen als genoemd] mmHg en gemiddelde gradient [alleen als genoemd] mmHg, effectief klepoppervlak [alleen als genoemd] cm2.
- Tricuspidalisklep: [natieve klep/bioprothese/mechanische kunstklep], morfologisch [normaal/degeneratief/prolaps], er is [geen/lichte/matige/ernstige] insufficiëntie, [zonder/met] toegevoegde structuur.
* Systolische pulmonale druk afgeleid uit TI [alleen als genoemd] mmHg + CVD.
- Pulmonalisklep is [normaal/sclerotisch], er is [geen/lichte/matige/ernstige] insufficiëntie.
- Aorta ascendens is [niet/mild/matig/aneurysmatisch] gedilateerd, graad [I/II/III/IV/V] atheromatose van de aortawand.
- Pulmonale arterie is [niet/mild/matig/aneurysmatisch] gedilateerd.
- Vena cava inferior/levervenes zijn [niet/mild/matig/ernstig] verbreed [met/zonder] ademvariatie.
- Pericard: er is [geen/mild/matig/uitgesproken] pericardvocht.

VEILIGHEIDSCHECK: Elk cijfer moet ECHT in het dictaat staan!
TERMINOLOGIE CHECK: Gebruik ALLEEN correcte medische Nederlandse termen!
"""
        else:
            # Template for spoedconsult, raadpleging, consult with strict 'niet vermeld' approach
            template_instruction = f"""
BELANGRIJK: U krijgt een intuïtief dictaat van een cardioloog. Dit betekent dat de informatie:
- Niet in de juiste volgorde staat
- In informele bewoordingen kan zijn
- Correcties kan bevatten
- Heen en weer kan springen tussen onderwerpen

KRITIEKE ANTI-HALLUCINATIE REGEL: VERZIN ABSOLUUT GEEN MEDISCHE GEGEVENS!

STRIKT STRAMIEN REGELS:
- BEHOUD ALLE TEMPLATE LIJNEN - laat geen enkele regel weg
- Voor elke lijn: vul ALLEEN in wat EXPLICIET genoemd is
- Voor niet-genoemde informatie: gebruik "niet vermeld"
- GEEN gissingen, GEEN aannames, GEEN logische afleidingen
- VEILIGHEID EERST: beter "niet vermeld" dan verzonnen data

CORRECTE MEDISCHE NEDERLANDSE TERMINOLOGIE:
- Gebruik ALTIJD correcte medische Nederlandse termen
- GEEN samengestelde woorden

VOLLEDIGE TEMPLATE STRUCTUUR:

Reden van komst: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Voorgeschiedenis: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Persoonlijke antecedenten: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Familiaal
- prematuur coronair lijden: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
- plotse dood: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Beroep: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Usus:
- nicotine: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
- ethyl: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
- druggebruik: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Anamnese
Retrosternale last: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Dyspneu: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Palpitaties: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Zwelling onderste ledematen: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Draaierigheid/syncope: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Lichamelijk onderzoek
Cor: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Longen: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Perifeer: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Jugulairen: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Aanvullend onderzoek
ECG op raadpleging ({today}):
- ritme: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
- PR: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
- QRS: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
- repolarisatie: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
- QTc: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Fietsproef op raadpleging ({today}):
[alleen invullen als expliciet genoemd, anders "niet vermeld"]
TTE op raadpleging ({today}):
Linker ventrikel: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Regionaal: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Rechter ventrikel: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Diastole: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Atria: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Aortadimensies: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Mitralisklep: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Aortaklep: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Pulmonalisklep: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Tricuspidalisklep: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Pericard: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Recente biochemie op datum ({today}):
- Hb: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
- Creatinine en eGFR: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
- LDL: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
- HbA1c: [alleen invullen als expliciet genoemd, anders "niet vermeld"]
Besluit
[alleen invullen als expliciet genoemd, anders "niet vermeld"]

VEILIGHEIDSCHECK: Elk gegeven moet ECHT in het dictaat staan!
ANTI-HALLUCINATIE: Bij twijfel altijd "niet vermeld" gebruiken!
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

        # Perform quality control review
        structured = quality_control_review(structured, corrected_transcript)

        # Check for hallucination (only if not disabled)
        if not disable_hallucination:
            is_hallucination, hallucination_msg = detect_hallucination(structured, corrected_transcript)
            
            if is_hallucination:
                # If hallucination detected, show warning and original transcript
                error_msg = f"🚨 Mogelijk hallucinatie gedetecteerd!\n\n{hallucination_msg}\n\nHet systeem heeft mogelijk medische gegevens verzonnen die niet in het originele dictaat stonden. Controleer het originele dictaat hieronder en probeer opnieuw met een duidelijker opname.\n\nOrigineel dictaat:\n{corrected_transcript}"
                return render_template('index.html', 
                                     error=error_msg,
                                     verslag_type=verslag_type)

        return render_template('index.html', 
                             transcript=corrected_transcript,
                             structured=structured,
                             verslag_type=verslag_type)

    except Exception as e:
        return render_template('index.html', error=f"Er is een fout opgetreden: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

