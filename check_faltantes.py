import os, logging, imaplib, email, re, sys
from email.utils import parsedate_to_datetime
os.environ['DJANGO_SETTINGS_MODULE'] = 'hospital_document_management.settings'
logging.disable(logging.CRITICAL)
import django; django.setup()

from correspondencia.models import CorreoEntrante
from datetime import datetime, date, time as dtime, timezone as tz
import pytz

col_tz = pytz.timezone('America/Bogota')
hoy = date.today()
hora_corte = datetime.combine(hoy, dtime(11, 30, 0), tzinfo=col_tz)

M = imaplib.IMAP4_SSL('imap.gmail.com')
M.login('Correspondenciaesesarare@gmail.com', 'kheb oroj oosc cfli')

# Paso 1: Buscar en [Gmail]/Todos los correos del dia y filtrar faltantes
M.select('"[Gmail]/Todos"', readonly=True)
date_str = hoy.strftime('%d-%b-%Y')
typ, data = M.search(None, f'SINCE {date_str}')
uids = data[0].split() if data[0] else []
bd_ids = set(CorreoEntrante.objects.values_list('message_id', flat=True))

faltantes = []
for i in range(0, len(uids), 50):
    batch = b','.join(uids[i:i+50])
    typ2, msg_data = M.fetch(batch, '(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID DATE FROM SUBJECT)] FLAGS RFC822.SIZE X-GM-LABELS)')
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            raw_meta = response_part[0].decode()
            msg = email.message_from_bytes(response_part[1])
            mid = msg.get('Message-ID', '').strip('<>').strip()
            date_hdr = msg.get('Date', '')
            try:
                msg_date = parsedate_to_datetime(date_hdr)
                if msg_date.tzinfo is None:
                    msg_date = msg_date.replace(tzinfo=tz.utc)
            except:
                continue
            if msg_date >= hora_corte and mid and mid not in bd_ids:
                subj_raw = msg.get('Subject', '')
                if subj_raw:
                    decoded = email.header.decode_header(subj_raw)
                    parts = []
                    for p, charset in decoded:
                        if isinstance(p, bytes):
                            parts.append(p.decode(charset or 'utf-8', errors='replace'))
                        else:
                            parts.append(p)
                    subj_raw = ''.join(parts)
                
                is_seen = '\\Seen' in raw_meta
                size_match = re.search(r'RFC822\.SIZE (\d+)', raw_meta)
                size_kb = int(size_match.group(1)) / 1024 if size_match else 0
                label_match = re.search(r'X-GM-LABELS \(([^)]*)\)', raw_meta)
                labels = label_match.group(1) if label_match else ''
                
                faltantes.append({
                    'mid': mid, 'date': msg_date, 'from': msg.get('From',''),
                    'subject': subj_raw, 'seen': is_seen, 'size_kb': size_kb,
                    'labels': labels, 'raw_meta': raw_meta
                })

M.close()

# Paso 2: Verificar cuales estan en INBOX (una sola busqueda)
M.select('INBOX', readonly=True)
inbox_mids = set()
for f in faltantes:
    typ3, data3 = M.search(None, f'HEADER Message-ID "<{f["mid"]}>"')
    if data3[0].strip():
        inbox_mids.add(f['mid'])
M.close()
M.logout()

# Mostrar resultados
print(f"=== DIAGNOSTICO DE {len(faltantes)} CORREOS FALTANTES (desde 11:30 AM) ===\n")
for i, f in enumerate(faltantes, 1):
    hora = f['date'].astimezone(col_tz).strftime('%H:%M')
    in_inbox = f['mid'] in inbox_mids
    print(f"CORREO {i}: [{hora}] {f['subject'][:70]}")
    print(f"  De: {f['from'][:60]}")
    print(f"  Message-ID: {f['mid'][:80]}")
    print(f"  En INBOX: {'SI' if in_inbox else 'NO'}")
    print(f"  Leido (Seen): {'SI' if f['seen'] else 'NO'}")
    print(f"  Labels Gmail: {f['labels'][:100] if f['labels'] else '(ninguna)'}")
    print(f"  Tamano: {f['size_kb']:.0f} KB")
    
    # Diagnostico
    if not in_inbox and not f['seen']:
        print(f"  >> CAUSA: Un filtro de Gmail movio este correo fuera de INBOX.")
        print(f"            El sistema SOLO leia INBOX, nunca lo vio.")
    elif not in_inbox and f['seen']:
        print(f"  >> CAUSA: Filtro de Gmail lo movio fuera de INBOX + fue leido manualmente.")
    elif in_inbox and not f['seen']:
        print(f"  >> CAUSA: Esta en INBOX, no leido. Celery aun no lo procesa (pendiente).")
    elif in_inbox and f['seen']:
        print(f"  >> CAUSA: En INBOX, leido, pero NO en BD. Posible error al procesarlo.")
    print()

sys.stdout.flush()
