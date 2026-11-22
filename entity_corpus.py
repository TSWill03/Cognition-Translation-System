"""Original synthetic corpus. No private book text; references are authored templates."""
import re

NAMES=[
 ("Lith","Selia","Derios"),("Solus","Eria","Valdor"),("Thalren","Nyvra","Eryndor"),
 ("Aster","Mira","Avelorn"),("Rose","Ash","Dunmere"),("Hope","May","Ravenhold"),
 ("Will","Grace","Stoneford"),("Orin","Tess","Varkesh"),("Kair","Liora","Nym Vale"),
 ("Vael","Sera","Ithmar"),("Silver","Dawn","Blackwater"),("Riven","Nessa","Torvyn"),
 ("Reed","Iris","Northwind"),("Eldric","Zhara","Caelmont"),("Aerion","Vesper","Draeven"),
]
# Each template declares required entity mentions independently of automatic matching.
# 15 name groups × 10 paired templates × 2 directions = 300 original cases.
TEMPLATES=[
 ('dialogue','“Do not open the gate,” {q} said. “{p} has not returned yet.”',
  '“Não abra o portão”, disse {q}. “{p} ainda não voltou.”','pq'),
 ('place','{p} met {q} near the city of {c}. {q} remembered the name of {p}.',
  '{p} encontrou {q} perto da cidade de {c}. {q} se lembrou do nome de {p}.','pqcqp'),
 ('negation','{p} did not give the sword to {q}. Neither of them left {c}.',
  '{p} não entregou a espada a {q}. Nenhum dos dois saiu de {c}.','pqc'),
 ('quantity','{q} gave {p} 3 vials, not 30. Keep them below 8 °C for 24 hours.',
  '{q} entregou a {p} 3 frascos, não 30. Mantenha-os abaixo de 8 °C por 24 horas.','qp'),
 ('terminology','{p} repaired the mana core. {q} hid the silver seal in {c}.',
  '{p} reparou o núcleo de mana. {q} escondeu o selo de prata em {c}.','pqc'),
 ('order','First {p} locked the door, then {q} touched the rune. Only afterward did the light disappear.',
  'Primeiro {p} trancou a porta, depois {q} tocou a runa. Só depois a luz desapareceu.','pq'),
 ('coreference','{p} lost his shield. {q} returned it to him before she entered {c}.',
  '{p} perdeu seu escudo. {q} o devolveu a ele antes de entrar em {c}.','pqc'),
 ('ambiguous','Hope is not lost. The rose grew beside the gate. May I enter? {p} asked {q}.',
  'A esperança não está perdida. A rosa cresceu ao lado do portão. Posso entrar? {p} perguntou a {q}.','pq'),
 ('layout','“Stay here, {p}.”\n\n{q} lowered her voice.\n\nThe road to {c} was closed.',
  '“Fique aqui, {p}.”\n\n{q} baixou a voz.\n\nA estrada para {c} estava fechada.','pqc'),
 ('idiom','After months of work, {p} found the silver seal out of the blue. {q} was relieved.',
  'Após meses de trabalho, {p} encontrou o selo de prata de forma inesperada. {q} ficou aliviada.','pq'),
]
TERMS={'en':{'mana core':'núcleo de mana','silver seal':'selo de prata'},
       'pt':{'núcleo de mana':'mana core','selo de prata':'silver seal'}}

def corpus():
 rows=[]
 for g,(p,q,c) in enumerate(NAMES):
  names=dict(p=p,q=q,c=c)
  for t,(domain,en,pt,mentions) in enumerate(TEMPLATES):
   for src,source,reference in [('en',en,pt),('pt',pt,en)]:
    context=(f"The man named {p} is a traveler. The woman named {q} is a healer. The city named {c} is their home."
             if src=='en' else
             f"O homem chamado {p} é um viajante. A mulher chamada {q} é uma curandeira. A cidade chamada {c} é sua casa.")
    expected={}
    for key in mentions:expected[names[key]]=expected.get(names[key],0)+1
    glossary={p:p,q:q,c:c,**TERMS[src]}
    text=source.format(**names)
    terms={v:len(re.findall(r'(?<!\w)'+re.escape(k)+r'(?!\w)',text,re.I)) for k,v in TERMS[src].items() if re.search(r'(?<!\w)'+re.escape(k)+r'(?!\w)',text,re.I)}
    rows.append(dict(id=f'{src}-{g:02d}-{t:02d}',source=src,target='pt' if src=='en' else 'en',
      text=text,reference=reference.format(**names),context=context,group=g,split='development' if g<5 else 'name-holdout',
      domain=domain,kind='synthetic',expected=expected,expected_terms=terms,entities=list(expected),
      all_names=[p,q,c],glossary=glossary,roles={p:'male',q:'female',c:'place'}))
 return rows
