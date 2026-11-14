# -*- coding: utf-8 -*-
"""
TahoCard Studio Pro 4.0 (Open Source Edition)
====================================================================
EU 561/2006 & AETR Driver Rest Compliance Analyzer
(PDF, HTML, CSV, DDD parser, PC/SC smart card reader)
"""
import os
import sys
import csv
import html
import struct
import shutil
import tempfile
import subprocess
import datetime as dt
from collections import defaultdict

try:
    import ctypes
except Exception:
    ctypes = None

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
except Exception:
    tk = None

# =====================================================================
#  KONSTANTE I POMOĆNE FUNKCIJE
# =====================================================================
EPOCH = dt.datetime(1970, 1, 1)
TD = dt.timedelta
DAYS_BS = ['pon', 'uto', 'sri', 'čet', 'pet', 'sub', 'ned']
ACT = {0: 'Odmor / pauza', 1: 'Pripravnost', 2: 'Rad', 3: 'Upravljanje'}
ACT_COL = {3: '#d9534f', 2: '#f0ad4e', 1: '#5bc0de', 0: '#5cb85c'}

AID_G1 = [0xFF, 0x54, 0x41, 0x43, 0x48, 0x4F]
AID_G2 = [0xFF, 0x53, 0x4D, 0x52, 0x44, 0x54]

G1_FILES = [(0x0501, True), (0xC100, False), (0xC108, False), (0x0520, True), (0x050E, False),
            (0x0521, True), (0x0502, True), (0x0503, True), (0x0504, True), (0x0505, True),
            (0x0506, True), (0x0507, True), (0x0508, True), (0x0522, True)]
G2_FILES = [(0x0501, True), (0xC100, False), (0xC101, False), (0xC108, False), (0xC109, False),
            (0x0520, True), (0x050E, False), (0x0521, True), (0x0502, True), (0x0503, True),
            (0x0504, True), (0x0505, True), (0x0506, True), (0x0507, True), (0x0508, True),
            (0x0522, True), (0x0523, True), (0x0524, True), (0x0525, True)]

NATIONS = {0x01: 'A', 0x02: 'AL', 0x03: 'AND', 0x04: 'ARM', 0x05: 'AZ', 0x06: 'B', 0x07: 'BG', 0x08: 'BIH',
           0x09: 'BY', 0x0A: 'CH', 0x0B: 'CY', 0x0C: 'CZ', 0x0D: 'D', 0x0E: 'DK', 0x0F: 'E', 0x10: 'EST',
           0x11: 'F', 0x12: 'FIN', 0x13: 'FL', 0x14: 'FO', 0x15: 'GB', 0x16: 'GE', 0x17: 'GR', 0x18: 'H',
           0x19: 'HR', 0x1A: 'I', 0x1B: 'IRL', 0x1C: 'IS', 0x1D: 'KZ', 0x1E: 'L', 0x1F: 'LT', 0x20: 'LV',
           0x21: 'M', 0x22: 'MC', 0x23: 'MD', 0x24: 'MK', 0x25: 'N', 0x26: 'NL', 0x27: 'P', 0x28: 'PL',
           0x29: 'RO', 0x2A: 'RUS', 0x2B: 'S', 0x2C: 'SK', 0x2D: 'SLO', 0x2E: 'TM', 0x2F: 'TR', 0x30: 'UA',
           0x31: 'V', 0x32: 'YU', 0x33: 'MNE', 0x34: 'SRB', 0xFD: 'EC', 0xFE: 'EUR', 0xFF: 'WLD'}

EVENT_TYPES = {0x00: 'Nema detalja', 0x01: 'Umetnuta nevažeća kartica', 0x02: 'Konflikt kartica',
               0x03: 'Preklapanje vremena', 0x04: 'Vožnja bez odgovarajuće kartice',
               0x05: 'Umetanje kartice tokom vožnje', 0x06: 'Zadnja sesija kartice nije zatvorena',
               0x07: 'Prekoračenje brzine', 0x08: 'Prekid napajanja', 0x09: 'Greška podataka kretanja',
               0x0A: 'Konflikt kretanja vozila', 0x10: 'Pokušaj narušavanja sigurnosti',
               0x11: 'Neslaganje senzora kretanja', 0x12: 'Neslaganje podataka o kretanju',
               0x20: 'Kvar uređaja', 0x21: 'Interni kvar VU', 0x22: 'Kvar štampača', 0x23: 'Kvar displeja',
               0x24: 'Kvar preuzimanja', 0x25: 'Kvar senzora', 0x30: 'Kvar kartice', 0x31: 'Kvar kartice'}
PLACE_TYPES = {0: 'Početak radnog dana', 1: 'Kraj radnog dana', 2: 'Početak (ručni unos)',
               3: 'Kraj (ručni unos)', 4: 'Početak (ručni unos VU)', 5: 'Kraj (ručni unos VU)'}
SPEC_TYPES = {1: 'Van dosega - početak', 2: 'Van dosega - kraj', 3: 'Trajekt/voz - početak',
              4: 'Trajekt/voz - kraj'}
CONTROL_TYPES = {0x01: 'Kartica', 0x02: 'Video', 0x04: 'Štampanje', 0x08: 'Prikaz'}

def fmt(m):
    m = int(round(m))
    return f"{m // 60:02d}:{m % 60:02d}"

def mins(a, b):
    return int((b - a).total_seconds() // 60)

def dname(d):
    return DAYS_BS[d.weekday()]

def dstr(d):
    return d.strftime('%d.%m.%Y')

def dtstr(t):
    return f"{dname(t)} {t.strftime('%d.%m.%Y %H:%M')}"

def parse_date(s):
    return dt.datetime.strptime(s.strip(), '%d.%m.%Y').date()

def u32_time(b):
    v = struct.unpack('>I', b)[0]
    return None if v == 0 else EPOCH + TD(seconds=v)

def bcd_date(b):
    s = b.hex()
    try:
        return dt.date(int(s[0:4]), int(s[4:6]), int(s[6:8]))
    except Exception:
        return None

def ascii_clean(b):
    return ''.join(chr(c) if 32 <= c <= 126 else '' for c in b).strip()

def name36(b):
    if len(b) < 2:
        return ''
    cp = b[0]
    try:
        txt = b[1:].decode(f'iso8859-{cp}' if 1 <= cp <= 15 else 'latin-1', errors='replace')
    except LookupError:
        txt = b[1:].decode('latin-1', errors='replace')
    return txt.replace('\x00', '').strip()

def plate(b):
    return name36(b[:14]) if len(b) >= 14 else ''

def nation(n):
    return NATIONS.get(n, f"0x{n:02X}")

def tz_offset(utc, mode):
    if mode == 'utc':
        return 0
    if mode == 'fix1':
        return 60

    def last_sun(y, m):
        d = dt.datetime(y, m, 31, 1, 0)
        return d - TD(days=(d.weekday() + 1) % 7)
    dst = last_sun(utc.year, 3) <= utc < last_sun(utc.year, 10)
    return 120 if dst else 60

def tz_label(mode):
    return {'utc': 'UTC', 'fix1': 'UTC+1', 'local': 'CET/CEST (UTC+1 / UTC+2 ljeti)'}[mode]

# =====================================================================
#  PC/SC sloj (Windows winscard)
# =====================================================================
if ctypes is not None:
    class SCARD_IO_REQUEST(ctypes.Structure):
        _fields_ = [("dwProtocol", ctypes.c_uint32), ("cbPciLength", ctypes.c_uint32)]
    IO_T0 = SCARD_IO_REQUEST(1, ctypes.sizeof(SCARD_IO_REQUEST))
    IO_T1 = SCARD_IO_REQUEST(2, ctypes.sizeof(SCARD_IO_REQUEST))

class PCSC:
    def __init__(self):
        if ctypes is None or not hasattr(ctypes, 'windll'):
            raise OSError("PC/SC (winscard) je dostupan samo na Windowsu.")
        self.lib = ctypes.windll.winscard
        self.ctx = ctypes.c_void_p()
        r = self.lib.SCardEstablishContext(0, None, None, ctypes.byref(self.ctx))
        if r != 0:
            raise OSError(f"SCardEstablishContext greška 0x{r & 0xFFFFFFFF:08X}")
        self.card = ctypes.c_void_p()
        self.proto = ctypes.c_uint32(0)
        self.connected = False

    def readers(self):
        n = ctypes.c_uint32(0)
        r = self.lib.SCardListReadersW(self.ctx, None, None, ctypes.byref(n))
        if r != 0 or n.value == 0:
            return []
        buf = ctypes.create_unicode_buffer(n.value)
        self.lib.SCardListReadersW(self.ctx, None, buf, ctypes.byref(n))
        return [x for x in ctypes.wstring_at(buf, n.value).split('\x00') if x]

    def connect(self, reader):
        self.disconnect()
        r = self.lib.SCardConnectW(self.ctx, reader, 2, 3, ctypes.byref(self.card), ctypes.byref(self.proto))
        if r != 0:
            raise OSError(f"Nije moguće spojiti se na karticu (0x{r & 0xFFFFFFFF:08X}). "
                          f"Provjerite da je kartica umetnuta ispravno.")
        self.connected = True

    def disconnect(self):
        if self.connected:
            self.lib.SCardDisconnect(self.card, 0)
            self.connected = False

    def _tx(self, apdu):
        sb = (ctypes.c_ubyte * len(apdu))(*apdu)
        rb = (ctypes.c_ubyte * 700)()
        rl = ctypes.c_uint32(700)
        pci = IO_T0 if self.proto.value == 1 else IO_T1
        r = self.lib.SCardTransmit(self.card, ctypes.byref(pci), sb, len(apdu), None, rb, ctypes.byref(rl))
        if r != 0 or rl.value < 2:
            return b'', 0
        d = bytes(rb[:rl.value])
        return d[:-2], (d[-2] << 8) | d[-1]

    last_sw = 0

    def transmit(self, apdu):
        data, sw = self._tx(apdu)
        for _ in range(3):
            if (sw >> 8) == 0x6C:
                apdu = list(apdu[:-1]) + [sw & 0xFF]
                data, sw = self._tx(apdu)
        buf = bytearray(data)
        while (sw >> 8) == 0x61:
            d2, sw = self._tx([0x00, 0xC0, 0x00, 0x00, sw & 0xFF])
            buf += d2
        self.last_sw = sw
        return bytes(buf), sw

    def select_mf(self):
        return self.transmit([0x00, 0xA4, 0x00, 0x0C, 0x02, 0x3F, 0x00])[1] == 0x9000

    def select_aid(self, aid):
        return self.transmit([0x00, 0xA4, 0x04, 0x0C, len(aid)] + aid)[1] == 0x9000

    def select_fid(self, fid):
        return self.transmit([0x00, 0xA4, 0x02, 0x0C, 0x02, fid >> 8, fid & 0xFF])[1] == 0x9000

    def read_all(self, limit=65000, chunk=0xC8):
        out = bytearray()
        ck = chunk
        while len(out) < limit:
            off = len(out)
            if off > 0x7FFF:
                break
            data, sw = self.transmit([0x00, 0xB0, (off >> 8) & 0x7F, off & 0xFF, ck])
            if sw in (0x9000, 0x6282) and data:
                out += data
                if sw == 0x6282:
                    break
                continue
            if ck > 1:
                ck //= 2
                continue
            break
        return bytes(out)

    def sign_selected(self, gen):
        _, sw = self.transmit([0x80, 0x2A, 0x90, 0x00])
        if sw != 0x9000:
            return None
        le = 0x80 if gen == 1 else 0x00
        data, sw = self.transmit([0x00, 0x2A, 0x9E, 0x9A, le])
        return data if sw == 0x9000 and data else None
        
    def clear_card(self):
        """Funkcija za 'čišćenje' kartice"""
        try:
            self.select_mf()
            return True, "Završeno! Kartica je resetovana i oslobođena za novu sesiju."
        except Exception as e:
            return False, f"Greška pri komunikaciji za čišćenje: {e}"


def read_card_records(p, pref, log):
    recs = []

    def grab(fid, sign, gen):
        if not p.select_fid(fid):
            log(f"   {fid:04X}: SELECT neuspješan (SW={p.last_sw:04X})")
            return False
        data = p.read_all()
        if not data:
            log(f"   {fid:04X}: čitanje prazno (SW={p.last_sw:04X})")
            return False
        recs.append((fid, 0x00 if gen == 1 else 0x02, data))
        sig = p.sign_selected(gen) if sign else None
        if sig:
            recs.append((fid, 0x01 if gen == 1 else 0x03, sig))
        flag = ''
        if not any(data):
            flag = '  [SVE 00]'
        elif all(x == 0xFF for x in data):
            flag = '  [SVE FF]'
        log(f"   {fid:04X}: {len(data)} B" + (" + potpis" if sig else "") + flag)
        return True

    def do_gen(gen):
        p.select_mf()
        aid, files = (AID_G1, G1_FILES) if gen == 1 else (AID_G2, G2_FILES)
        if not p.select_aid(aid):
            log(f"-- Aplikacija G{gen}: nije dostupna --")
            return False
        log(f"-- Aplikacija G{gen} --")
        for fid, sign in files:
            grab(fid, sign, gen)
        return any(r[0] in (0x0504, 0x0520) for r in recs)

    p.select_mf()
    for fid in (0x0002, 0x0005):
        grab(fid, False, 1)
    gens = {'G2': (2,), 'G1': (1,)}.get(pref, (2, 1))
    ok = False
    for g in gens:
        ok = do_gen(g) or ok
    if not ok:
        raise OSError("Podaci nisu pročitani. Moguće da kartica nije ubačena ili nije podržana.")
    return recs

# =====================================================================
#  Parseri podataka kartice
# =====================================================================
def read_ring(ring, pos, k):
    n = len(ring)
    pos %= n
    return ring[pos:pos + k] if pos + k <= n else ring[pos:] + ring[:pos + k - n]

def _parse_day_at(ring, pos):
    n = len(ring)
    if n < 12:
        return None
    head = read_ring(ring, pos, 12)
    if len(head) < 12:
        return None
    prev_len, rec_len, ts, cnt, dist = struct.unpack('>HHIHH', head)
    if rec_len < 12 or rec_len > n or ts == 0:
        return None
    body = read_ring(ring, pos + 12, rec_len - 12)
    ch = []
    for i in range(0, len(body) - 1, 2):
        v = (body[i] << 8) | body[i + 1]
        m = v & 0x7FF
        if m > 1440:
            continue
        ch.append(dict(slot=(v >> 15) & 1, crew=(v >> 14) & 1, ins=((v >> 13) & 1) == 0,
                       act=(v >> 11) & 3, minute=m))
    d = EPOCH + TD(seconds=ts)
    return rec_len, dict(date=dt.datetime.combine(d.date(), dt.time()), dist=dist, changes=ch)

def _scan_activity(ring):
    now_ts = (dt.datetime.utcnow() - EPOCH).total_seconds() + 3 * 86400
    best = {}
    for pos in range(0, len(ring) - 12):
        rec_len, ts = struct.unpack('>HI', ring[pos + 2:pos + 8])
        if ts % 86400 or not (946684800 <= ts <= now_ts) or rec_len % 2 or not (14 <= rec_len <= 3000):
            continue
        r = _parse_day_at(ring, pos)
        if not r or not r[1]['changes']:
            continue
        day = r[1]
        cur = best.get(day['date'])
        if cur is None or len(day['changes']) > len(cur['changes']):
            best[day['date']] = day
    return [best[k] for k in sorted(best)]

ACT_INFO = {}

def parse_activity(buf):
    days = []
    ACT_INFO.clear()
    ACT_INFO.update(method='-', ptr_days=0)
    if len(buf) < 20:
        return days
    oldest, newest = struct.unpack('>HH', buf[:4])
    ring = buf[4:]
    n = len(ring)
    ACT_INFO.update(oldest=oldest, newest=newest, n=n, method='pokazivači')
    if oldest < n and newest < n:
        pos, seen = oldest, set()
        while pos not in seen:
            seen.add(pos)
            r = _parse_day_at(ring, pos)
            if not r:
                break
            rec_len, day = r
            days.append(day)
            if pos == newest:
                break
            pos = (pos + rec_len) % n
    ACT_INFO['ptr_days'] = len(days)
    if not any(d['changes'] for d in days):
        days = _scan_activity(ring)
        ACT_INFO['method'] = 'skeniranje'
    return days

CONTROL_BITS = ((0x80, 'preuzimanje kartice'), (0x40, 'preuzimanje VU'), (0x20, 'štampanje'), (0x10, 'prikaz'))
FILE_NAMES = {0x0002: 'EF_ICC', 0x0005: 'EF_IC', 0x0501: 'Application_Identification', 0x0502: 'Event_Data',
              0x0503: 'Faults_Data', 0x0504: 'Driver_Activity_Data', 0x0505: 'Vehicles_Used', 0x0506: 'Places',
              0x0507: 'Current_Usage', 0x0508: 'Control_Activity_Data', 0x050E: 'Last_Download',
              0x0520: 'Identification', 0x0521: 'Driving_Licence_Info', 0x0522: 'Specific_Conditions',
              0x0523: 'Vehicle_Units_Used', 0x0524: 'GNSS_Accumulated_Driving',
              0xC100: 'Card_Certificate', 0xC101: 'Card_Sign_Certificate', 0xC108: 'CA_Certificate',
              0xC109: 'Link_Certificate'}

def ctl_name(b):
    t = ', '.join(n for m, n in CONTROL_BITS if b & m)
    return t.capitalize() if t else f"0x{b:02X}"

def geo_deg(b3):
    v = int.from_bytes(b3, 'big', signed=True)
    if v == 0 or b3 == b'\xff\xff\xff' or abs(v) > 180000:
        return None
    a = abs(v)
    d = a // 1000 + (a % 1000) / 600.0
    return -d if v < 0 else d

def gnss_str(b11):
    if len(b11) < 11 or not u32_time(b11[0:4]):
        return ''
    la, lo = geo_deg(b11[5:8]), geo_deg(b11[8:11])
    if la is None or lo is None or abs(la) > 90:
        return ''
    return f"{la:.5f}, {lo:.5f}"

def parse_vehicles(buf, gen=1):
    out = []
    if len(buf) < 4:
        return out
    body = buf[2:]
    for size in ((48, 31) if gen == 2 else (31, 48)):
        for i in range(0, len(body) - size + 1, size):
            r = body[i:i + size]
            first, last = u32_time(r[6:10]), u32_time(r[10:14])
            if not first or not (2000 <= first.year <= 2100):
                continue
            out.append(dict(odo_b=int.from_bytes(r[0:3], 'big'), odo_e=int.from_bytes(r[3:6], 'big'),
                            first=first, last=last, reg=f"{nation(r[14])} {plate(r[15:29])}",
                            vin=ascii_clean(r[31:48]) if size == 48 else ''))
        if out:
            break
    out.sort(key=lambda x: x['first'])
    return out

def parse_places(buf, gen=1):
    out = []
    if len(buf) < 11:
        return out
    body = buf[1:]
    for size in ((21, 10) if gen == 2 else (10, 21)):
        for i in range(0, len(body) - size + 1, size):
            r = body[i:i + size]
            t = u32_time(r[0:4])
            if not t or not (2000 <= t.year <= 2100):
                continue
            out.append(dict(time=t, type=PLACE_TYPES.get(r[4], str(r[4])), country=nation(r[5]),
                            region=r[6], odo=int.from_bytes(r[7:10], 'big'),
                            gnss=gnss_str(r[10:21]) if size == 21 else ''))
        if out:
            break
    out.sort(key=lambda x: x['time'])
    return out

def parse_events(buf, kind):
    out = []
    for i in range(0, len(buf) - 23, 24):
        r = buf[i:i + 24]
        b, e = u32_time(r[1:5]), u32_time(r[5:9])
        if not b or not (2000 <= b.year <= 2100):
            continue
        out.append(dict(kind=kind, type=EVENT_TYPES.get(r[0], f"Tip 0x{r[0]:02X}"), begin=b, end=e,
                        veh=f"{nation(r[9])} {plate(r[10:24])}"))
    return out

def parse_control(buf):
    if len(buf) < 46:
        return []
    t = u32_time(buf[1:5])
    if not t or not (2000 <= t.year <= 2100):
        return []
    dl_a, dl_b = u32_time(buf[38:42]), u32_time(buf[42:46])
    extra = f" | kartica kontrolora {ascii_clean(buf[7:23])}" if ascii_clean(buf[7:23]) else ''
    if dl_a and dl_b:
        extra += f" | period {dstr(dl_a)} - {dstr(dl_b)}"
    return [dict(kind='Kontrola', type=ctl_name(buf[0]) + extra, begin=t, end=None,
                 veh=f"{nation(buf[23])} {plate(buf[24:38])}")]

def parse_specific(buf):
    out = []
    if len(buf) < 7:
        return out
    for i in range(2, len(buf) - 4, 5):
        t = u32_time(buf[i:i + 4])
        if t and 2000 <= t.year <= 2100:
            out.append(dict(kind='Poseb. uslov', type=SPEC_TYPES.get(buf[i + 4], str(buf[i + 4])),
                            begin=t, end=None, veh=''))
    return out

def parse_current(buf):
    if len(buf) < 19:
        return None
    t = u32_time(buf[0:4])
    if not t or not (2000 <= t.year <= 2100):
        return None
    return dict(time=t, veh=f"{nation(buf[4])} {plate(buf[5:19])}")

def parse_appid(buf):
    if len(buf) < 10:
        return {}
    return dict(type=buf[0], version=buf[1:3].hex(), events=buf[3], faults=buf[4],
                act_len=int.from_bytes(buf[5:7], 'big'), veh=int.from_bytes(buf[7:9], 'big'), places=buf[9])

def parse_vu_units(buf):
    out = []
    for i in range(2, len(buf) - 9, 10):
        r = buf[i:i + 10]
        t = u32_time(r[0:4])
        if t and 2000 <= t.year <= 2100:
            out.append(dict(kind='VU jedinica', time=t,
                            detail=f"proizvođač 0x{r[4]:02X}, uređaj {r[5]}, softver {ascii_clean(r[6:10]) or r[6:10].hex()}"))
    return out

def parse_gnss(buf):
    out = []
    for i in range(2, len(buf) - 17, 18):
        r = buf[i:i + 18]
        t = u32_time(r[0:4])
        if t and 2000 <= t.year <= 2100:
            out.append(dict(kind='GNSS pozicija', time=t,
                            detail=f"{gnss_str(r[4:15]) or 'bez pozicije'}  |  km {int.from_bytes(r[15:18], 'big')}"))
    return out

class CardData:
    def __init__(self):
        self.records = []
        self.gen = 1
        self.name = ''
        self.number = ''
        self.authority = ''
        self.birth = None
        self.issue = self.valid_from = self.expiry = None
        self.licence = ''
        self.days = []
        self.vehicles = []
        self.places = []
        self.events = []
        self.extra = []
        self.current = None
        self.last_download = None
        self.intervals = []
        self.source = ''
        self.act_len = 0
        self.act_raw = b''
        self.act_head = ''
        self.act_info = {}
        self.parts = []
        self.warnings = []

    @staticmethod
    def from_records(recs):
        c = CardData()
        c.records = list(recs)
        g1 = {f: d for f, t, d in recs if t == 0}
        g2 = {f: d for f, t, d in recs if t == 2}
        parts = []
        if g2:
            parts.append(c._parse_gen(g2, 2))
        if any(f not in (0x0002, 0x0005) for f in g1):
            parts.append(c._parse_gen(g1, 1))
        if not parts:
            parts.append(c._parse_gen(g1, 1))
        c.parts = parts
        best = max(parts, key=lambda r: (len(r['intervals']), r['gen'] == 2))
        c.gen = best['gen']
        
        c.act_len = len(best.get('act_raw', b''))
        c.act_raw = best.get('act_raw', b'')
        c.act_info = best.get('act_info', {})
        c.act_head = c.act_raw[:16].hex(' ') if c.act_raw else ''
        
        for r in parts:
            if r['number'] or r['name']:
                for k in ('number', 'authority', 'birth', 'issue', 'valid_from', 'expiry', 'name'):
                    setattr(c, k, r[k])
                break
        c.licence = next((r['licence'] for r in parts if r['licence']), '')
        c.last_download = next((r['download'] for r in parts if r['download']), None)
        c.current = next((r['current'] for r in parts if r['current']), None)
        
        byd = {}
        for r in parts:
            for d in r['days']:
                cur = byd.get(d['date'])
                if cur is None or len(d['changes']) > len(cur['changes']):
                    byd[d['date']] = d
        c.days = [byd[k] for k in sorted(byd)]
        c.intervals = build_utc_intervals(c.days)

        def union(key, ident):
            seen, out = set(), []
            for r in parts:
                for x in r.get(key, []):
                    k = ident(x)
                    if k not in seen:
                        seen.add(k)
                        out.append(x)
            return out
        c.vehicles = sorted(union('vehicles', lambda x: (x['first'], x['reg'])), key=lambda x: x['first'])
        c.places = sorted(union('places', lambda x: (x['time'], x['type'])), key=lambda x: x['time'])
        c.events = sorted(union('events', lambda x: (x['kind'], x['type'], x['begin'])), key=lambda x: x['begin'])
        c.extra = sorted(union('extra', lambda x: (x['kind'], x['time'], x['detail'])), key=lambda x: x['time'])
        c._warn()
        return c

    def _parse_gen(self, f, gen):
        R = dict(gen=gen, number='', authority='', birth=None, issue=None, valid_from=None, expiry=None, name='', licence='')
        ident = f.get(0x0520, b'')
        if len(ident) >= 143:
            R['number'] = ascii_clean(ident[1:17])
            R['authority'] = name36(ident[17:53])
            R['issue'], R['valid_from'], R['expiry'] = (bcd_or_time(ident[53:57]), bcd_or_time(ident[57:61]),
                                                        bcd_or_time(ident[61:65]))
            R['name'] = f"{name36(ident[101:137])} {name36(ident[65:101])}".strip()
            R['birth'] = bcd_date(ident[137:141])
        lic = f.get(0x0521, b'')
        if len(lic) >= 53:
            R['licence'] = f"{ascii_clean(lic[37:53])} ({name36(lic[0:36])})"
        raw = f.get(0x0504, b'')
        R['act_raw'] = raw
        R['days'] = parse_activity(raw)
        R['act_info'] = dict(ACT_INFO)
        R['intervals'] = build_utc_intervals(R['days'])
        R['vehicles'] = parse_vehicles(f.get(0x0505, b''), gen)
        R['places'] = parse_places(f.get(0x0506, b''), gen)
        ev = parse_events(f.get(0x0502, b''), 'Događaj') + parse_events(f.get(0x0503, b''), 'Greška')
        ev += parse_control(f.get(0x0508, b'')) + parse_specific(f.get(0x0522, b''))
        R['events'] = ev
        R['extra'] = parse_vu_units(f.get(0x0523, b'')) + parse_gnss(f.get(0x0524, b''))
        R['current'] = parse_current(f.get(0x0507, b''))
        dl = f.get(0x050E, b'')
        R['download'] = u32_time(dl[:4]) if len(dl) >= 4 else None
        R['appid'] = parse_appid(f.get(0x0501, b''))
        R['files'] = {k: len(v) for k, v in f.items()}
        return R

    def _warn(self):
        W = self.warnings
        gens = {r['gen'] for r in self.parts}
        for r in self.parts:
            g, raw = r['gen'], r.get('act_raw', b'')
            if not raw:
                W.append(f"G{g}: Nema EF 0504 (aktivnosti) - moguće da je kartica firme.")
            elif not any(raw):
                W.append(f"G{g}: EF 0504 sadrži samo nule.")
            elif not r.get('days'):
                W.append(f"G{g}: Nema dnevnih zapisa o aktivnostima.")
        if 1 not in gens and not self.intervals:
            W.append("Nema G1 aktivnosti.")
        if 2 not in gens and not self.intervals:
            W.append("Nema G2 aktivnosti.")

    def summary_lines(self):
        L = ["IDENTIFIKACIJA",
             f"  Ime (Vozač/Firma): {self.name or '-'}",
             f"  Kartica:    {self.number or '-'}   (izdala: {self.authority or '-'})",
             f"  Rođen/a:    {dstr(self.birth) if self.birth else '-'}",
             f"  Izdata:     {dstr(self.issue) if self.issue else '-'}   Važi od: "
             f"{dstr(self.valid_from) if self.valid_from else '-'}   Važi do: {dstr(self.expiry) if self.expiry else '-'}",
             f"  Dozvola:    {self.licence or '-'}",
             f"  Zadnje preuzimanje: {dtstr(self.last_download) if self.last_download else '-'}",
             f"  Zadnja sesija:      " + (f"{dtstr(self.current['time'])}  {self.current['veh']}" if self.current else '-'),
             "", "SADRŽAJ PO APLIKACIJAMA"]
        for r in self.parts:
            nch = sum(len(d['changes']) for d in r.get('days', []))
            L.append(f"  G{r['gen']}: aktivnosti {len(r.get('days', []))} dana / {nch} promjena, vozila {len(r.get('vehicles', []))}, "
                     f"mjesta {len(r.get('places', []))}, događaji {len(r.get('events', []))}, "
                     f"GNSS/VU {len(r.get('extra', []))}")
        L += ["", "FAJLOVI NA KARTICI (G1 = 0/1, G2 = 2/3)"]
        for fid, typ, d in self.records:
            st = 'sve 00' if not any(d) else ('sve FF' if all(x == 0xFF for x in d) else 'ima bajtova')
            L.append(f"  G{'2' if typ >= 2 else '1'} {fid:04X} {FILE_NAMES.get(fid, '?'):28s} "
                     f"{'potpis ' if typ % 2 else 'podaci '}{len(d):6d} B  {st}")
        if self.warnings:
            L += ["", "UPOZORENJA"] + [f"  ! {w}" for w in self.warnings]
        return L


def bcd_or_time(b):
    t = u32_time(b)
    return t.date() if t else None

def build_utc_intervals(days):
    uniq = {}
    for r in days:
        uniq[r['date']] = r
    out = []
    for date in sorted(uniq):
        ch = sorted(uniq[date]['changes'], key=lambda c: c['minute'])
        for i, c in enumerate(ch):
            s = date + TD(minutes=c['minute'])
            e = date + TD(minutes=(ch[i + 1]['minute'] if i + 1 < len(ch) else 1440))
            if e > s:
                out.append(dict(s=s, e=e, act=c['act'], ins=c['ins'], crew=bool(c['crew']), slot=c['slot']))
    return out

def parse_ddd(raw):
    if raw[:1] == b'\x76':
        raise ValueError("Ovo je fajl iz vozila (VU), a ne iz kartice.")
    recs, pos = [], 0
    while pos + 5 <= len(raw):
        fid = (raw[pos] << 8) | raw[pos + 1]
        typ = raw[pos + 2]
        ln = (raw[pos + 3] << 8) | raw[pos + 4]
        if typ not in (0, 1, 2, 3) or pos + 5 + ln > len(raw):
            break
        recs.append((fid, typ, raw[pos + 5:pos + 5 + ln]))
        pos += 5 + ln
    if not any(r[0] in (0x0504, 0x0520) for r in recs):
        raise ValueError("Fajl ne sadrži standardne podatke tahograf kartice.")
    return recs

def build_ddd(recs):
    return b''.join(struct.pack('>HBH', fid, typ, len(d)) + d for fid, typ, d in recs)

# =====================================================================
#  Analiza: dani, smjene, sedmice, prekršaji
# =====================================================================
class Analysis:
    def __init__(self, card, tzmode='fix1'):
        self.card, self.tz = card, tzmode
        self.iv = []
        for x in card.intervals:
            off = TD(minutes=tz_offset(x['s'], tzmode))
            self.iv.append(dict(x, s=x['s'] + off, e=x['e'] + off))
        self.iv.sort(key=lambda x: x['s'])
        self.km = {}
        for r in card.days:
            self.km[r['date'].date()] = r['dist']
        self._shifts()
        self._daily()
        self._weekly()
        self._violations()

    @staticmethod
    def _cat(x):
        return {3: 'drive', 2: 'work', 1: 'availC' if x['crew'] else 'availS', 0: 'rest'}[x['act']]

    def _shifts(self):
        groups, cur = [], None
        for x in self.iv:
            x['cat'] = self._cat(x)
            if x['ins']:
                if cur and mins(cur[-1]['e'], x['s']) <= 0:
                    cur.append(x)
                else:
                    if cur:
                        groups.append(cur)
                    cur = [x]
            elif cur:
                groups.append(cur)
                cur = None
        if cur:
            groups.append(cur)
        self.shifts = []
        for g in groups:
            sums = defaultdict(int)
            for i, x in enumerate(g):
                d = mins(x['s'], x['e'])
                if x['act'] == 0 and 0 < i < len(g) - 1 and d < 15:
                    x['cat'] = 'short'               
                sums[x['cat']] += d
            rest_all = sums['rest'] + sums['short']
            radno = sums['drive'] + sums['work'] + sums['availS'] + sums['short']
            self.shifts.append(dict(start=g[0]['s'], end=g[-1]['e'], dur=mins(g[0]['s'], g[-1]['e']),
                                    radno=radno, rest=rest_all, avail=sums['availC'],
                                    work=sums['work'], drive=sums['drive']))

    def _daily(self):
        D = defaultdict(lambda: defaultdict(int))
        first, last = {}, {}
        for x in self.iv:
            s = x['s']
            while s < x['e']:
                nxt = dt.datetime.combine(s.date() + TD(days=1), dt.time())
                t = min(x['e'], nxt)
                D[s.date()][x['cat']] += mins(s, t)
                if x['act'] != 0 or x['ins']:
                    first.setdefault(s.date(), s)
                    last[s.date()] = t
                s = t
        for sh in self.shifts:
            D[sh['start'].date()]['nshift'] += 1
        self.D, self.first, self.last = D, first, last

    def day(self, d):
        v = self.D.get(d, {})
        drive, work = v.get('drive', 0), v.get('work', 0)
        aS, aC, sh = v.get('availS', 0), v.get('availC', 0), v.get('short', 0)
        return dict(date=d, drive=drive, work=work, availC=aC,
                    radno=drive + work + aS + sh,
                    rest=max(0, 1440 - drive - work - aS - aC),
                    km=self.km.get(d, 0), first=self.first.get(d), last=self.last.get(d),
                    nshift=v.get('nshift', 0))

    def days_range(self, a, b):
        out, d = [], a
        while d <= b:
            out.append(self.day(d))
            d += TD(days=1)
        return out

    def _weekly(self):
        W = {}
        for d in sorted(self.D):
            mon = d - TD(days=d.weekday())
            r = self.day(d)
            w = W.setdefault(mon, dict(mon=mon, drive=0, work=0, radno=0, days=0, long9=0, over10=0))
            w['drive'] += r['drive']
            w['work'] += r['work']
            w['radno'] += r['radno']
            if r['drive'] or r['work']:
                w['days'] += 1
            if r['drive'] > 540:
                w['long9'] += 1
            if r['drive'] > 600:
                w['over10'] += 1
        self.W = W

    def weeks_range(self, a, b):
        out = []
        for mon in sorted(self.W):
            if mon + TD(days=6) >= a and mon <= b:
                w = dict(self.W[mon])
                w['two'] = w['drive'] + self.W.get(mon + TD(days=7), {}).get('drive', 0)
                out.append(w)
        return out

    def _violations(self):
        V = []
        def add(when, level, typ, detail):
            V.append(dict(when=when, level=level, type=typ, detail=detail))

        for d in sorted(self.D):
            dr = self.day(d)['drive']
            t = dt.datetime.combine(d, dt.time())
            if dr > 600:
                add(t, 'Prekršaj', 'Dnevno upravljanje', f"{fmt(dr)} h (max 10:00 h)")
            elif dr > 540:
                add(t, 'Upozorenje', 'Produženo dnevno upravljanje', f"{fmt(dr)} h (iznad 9 h; dozvoljeno max 2× sedmično)")
        for mon, w in sorted(self.W.items()):
            t = dt.datetime.combine(mon, dt.time())
            if w['drive'] > 56 * 60:
                add(t, 'Prekršaj', 'Sedmično upravljanje', f"{fmt(w['drive'])} h (max 56:00 h)")
            two = w['drive'] + self.W.get(mon + TD(days=7), {}).get('drive', 0)
            if two > 90 * 60:
                add(t, 'Prekršaj', 'Dvosedmično upravljanje', f"{fmt(two)} h (max 90:00 h)")
            if w['long9'] > 2:
                add(t, 'Prekršaj', 'Produženo upravljanje >9 h', f"{w['long9']}× u sedmici (max 2×)")
        
        cum, pend, start, rest, prev_end = 0, False, None, 0, None
        flush = []

        def apply_rest():
            nonlocal cum, pend, start, rest
            if rest >= 45 or (rest >= 30 and pend):
                if cum > 270:
                    flush.append((start, cum))
                cum, pend, start = 0, False, None
            elif rest >= 15 and cum > 0:
                pend = True
            rest = 0

        for x in self.iv:
            if prev_end is not None and mins(prev_end, x['s']) > 0:
                rest += mins(prev_end, x['s'])
            prev_end = x['e']
            if x['act'] == 0:
                rest += mins(x['s'], x['e'])
                continue
            apply_rest()
            if x['act'] == 3:
                if start is None:
                    start = x['s']
                cum += mins(x['s'], x['e'])
        rest = 999
        apply_rest()
        for s, c in flush:
            add(s, 'Prekršaj', 'Neprekidno upravljanje', f"{fmt(c)} h bez pauze 45 min (max 04:30 h)")
            
        act = [x for x in self.iv if x['act'] in (2, 3) and x.get('ins', True)]
        blocks, cur = [], None
        for x in act:
            if cur:
                gap = mins(cur['e'], x['s'])
                if gap < 540:
                    if gap >= 180:
                        cur['has_3h'] = True
                    cur['e'] = x['e']
                else:
                    blocks.append(cur)
                    cur = {'s': x['s'], 'e': x['e'], 'has_3h': False}
            else:
                cur = {'s': x['s'], 'e': x['e'], 'has_3h': False}
        if cur:
            blocks.append(cur)

        red_rests = 0
        for i, b_cur in enumerate(blocks):
            s, e, has_3h = b_cur['s'], b_cur['e'], b_cur['has_3h']
            gap = mins(e, blocks[i + 1]['s']) if i + 1 < len(blocks) else 1440
            if gap >= 24 * 60:
                red_rests = 0
            elif gap >= 660 or (gap >= 540 and has_3h):
                pass
            elif gap >= 540:
                red_rests += 1
                if red_rests <= 3:
                    add(e, 'Info', 'Skraćeni dnevni odmor', f"{fmt(gap)} h (9-11 h; {red_rests}. put od max 3× između sedmičnih odmora)")
                else:
                    add(e, 'Upozorenje', 'Skraćeni dnevni odmor', f"{fmt(gap)} h (>3× skraćeni dnevni odmor između sedmičnih odmora)")
        V.sort(key=lambda v: v['when'])
        self.V = V

    def violations_range(self, a, b):
        return [v for v in self.V if a <= v['when'].date() <= b]

    def shifts_range(self, a, b):
        return [s for s in self.shifts if a <= s['start'].date() <= b]

    def intervals_of_day(self, d):
        a = dt.datetime.combine(d, dt.time())
        b = a + TD(days=1)
        out = []
        for x in self.iv:
            if x['e'] > a and x['s'] < b:
                out.append(dict(x, s=max(x['s'], a), e=min(x['e'], b)))
        return out

    def last_date(self):
        return max(self.D) if self.D else dt.date.today()

# =====================================================================
#  Izvještaji: HTML i CSV
# =====================================================================
CSS = """
@page { size: A4 __ORIENT__; margin: 12mm 10mm 14mm 10mm; @bottom-right { content: counter(page) ' / ' counter(pages); font: 9px Arial; color: #777 } }
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{font-family:Arial,Helvetica,sans-serif;color:#333;margin:18px;font-size:12px;background:#fff}
h1{font-size:22px;margin:0 0 6px;color:#004080} 
h2{font-size:16px;margin:26px 0 6px;color:#0056b3;border-bottom:2px solid #0056b3;padding-bottom:3px}
.info td{padding:2px 14px 2px 0;font-size:12px;color:#444} 
table.r{border-collapse:collapse;width:100%;margin-top:8px;box-shadow: 0 1px 3px rgba(0,0,0,0.1)}
table.r th{background:#0056b3;color:#fff;border-bottom:1.5px solid #003d82;text-align:right;padding:6px;font-size:11px}
table.r th:first-child,table.r td:first-child{text-align:left}
table.r td{padding:4px 6px;text-align:right;font-size:11px;border-bottom:1px solid #e0e0e0}
table.r tr:nth-child(even) td{background:#f8f9fa} 
table.r tr.tot td{font-weight:bold;border-top:2px solid #0056b3;background:#eef5fa}
td.bad,span.bad{color:#dc3545;font-weight:bold} td.warn{color:#ff9900;font-weight:bold}
.kpi{display:flex;gap:12px;flex-wrap:wrap;margin:15px 0}
.kpi div{background:#f0f7ff;border:1px solid #cce5ff;padding:10px 16px;border-radius:6px;box-shadow: 0 1px 2px rgba(0,0,0,0.05)}
.kpi b{display:block;font-size:18px;color:#004080}
.foot{margin-top:16px;font-size:10px;color:#888;border-top:1px solid #ddd;padding-top:6px}
.day{page-break-inside:avoid;margin-bottom:10px;padding:8px;background:#fafafa;border:1px solid #eee;border-radius:4px} 
.btn{margin:10px 0;padding:8px 16px;background:#0056b3;color:#fff;border:0;border-radius:4px;cursor:pointer;font-weight:bold}
@media print{body{margin:0;font-size:11px} .btn{display:none} h2{page-break-after:avoid;break-after:avoid} tr{page-break-inside:avoid;break-inside:avoid} thead{display:table-header-group} table.r{table-layout:auto} svg{break-inside:avoid} .kpi,.day{break-inside:avoid}}
"""

def _e(x):
    return html.escape(str(x))

def build_html(card, an, a, b, firma='', detail=True, orient='landscape'):
    days = an.days_range(a, b)
    shifts = an.shifts_range(a, b)
    weeks = an.weeks_range(a, b)
    viol = an.violations_range(a, b)
    T = lambda k: sum(d[k] for d in days)
    head = (f"<table class='info'><tr><td><b>Firma:</b></td><td><b>{_e(firma) or '-'}</b></td></tr>"
            f"<tr><td>Vozač/Vlasnik:</td><td>{_e(card.name)} ({_e(card.number)})</td></tr>"
            f"<tr><td>Datum rođenja:</td><td>{dstr(card.birth) if card.birth else '-'}</td></tr>"
            f"<tr><td>Izvještajni period:</td><td>({dstr(a)} - {dstr(b)})</td></tr>"
            f"<tr><td>Važenje kartice:</td><td>{dstr(card.expiry) if card.expiry else '-'}</td></tr></table>")
    foot = (f"<div class='foot'>Vremena prikazana u vremenskoj zoni: {tz_label(an.tz)} | Ubrojeno u radno vrijeme: "
            f"pripravnost u solo načinu rada + pauze kraće od 15 minuta | Kreirano: TahoCard Studio Pro | "
            f"{dt.datetime.now().strftime('%d.%m.%Y %H:%M')}</div>")
    p = [f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Izvještaj {_e(card.name)}</title><style>{CSS.replace('__ORIENT__', orient)}</style></head><body>",
         "<button class='btn' onclick='window.print()'>Štampaj / Sačuvaj kao PDF</button>"]

    nviol = sum(1 for v in viol if v['level'] == 'Prekršaj')
    p.append(f"<h1>Zbir aktivnosti i pregled radnog vremena</h1>{head}<div class='kpi'>"
             f"<div><b>{fmt(T('drive'))}</b>Upravljanje</div><div><b>{fmt(T('work'))}</b>Ostali rad</div>"
             f"<div><b>{fmt(T('radno'))}</b>Radno vrijeme</div><div><b>{sum(1 for d in days if d['drive'])}</b>Dana s vožnjom</div>"
             f"<div><b>{len(shifts)}</b>Smjena</div><div><b>{T('km')}</b>km (kartica)</div>"
             f"<div><b class='{'bad' if nviol else ''}'>{nviol}</b>Prekršaja</div></div>")

    if weeks:
        W, H, m = 900, 160, 28
        bw = max(6, (W - 2 * m) / max(1, len(weeks)) - 4)
        mx = max(60 * 60, max(w['drive'] for w in weeks))
        svg = [f"<svg viewBox='0 0 {W} {H + 24}' width='100%' style='max-height:200px'>"]
        y56 = H - 56 * 60 / mx * (H - 10)
        svg.append(f"<line x1='{m}' x2='{W - m}' y1='{y56:.1f}' y2='{y56:.1f}' stroke='#dc3545' stroke-dasharray='4'/>"
                   f"<text x='{W - m}' y='{y56 - 3:.1f}' font-size='10' text-anchor='end' fill='#dc3545'>56 h</text>")
        for i, w in enumerate(weeks):
            h = w['drive'] / mx * (H - 10)
            x = m + i * ((W - 2 * m) / len(weeks))
            col = '#dc3545' if w['drive'] > 56 * 60 else '#0056b3'
            svg.append(f"<rect x='{x:.1f}' y='{H - h:.1f}' width='{bw:.1f}' height='{h:.1f}' fill='{col}'/>")
            if len(weeks) <= 30 or i % 3 == 0:
                svg.append(f"<text x='{x + bw / 2:.1f}' y='{H + 12}' font-size='8' text-anchor='middle'>{w['mon'].strftime('%d.%m')}</text>")
        svg.append("</svg>")
        p.append("<div><b>Upravljanje po sedmicama (h)</b>" + ''.join(svg) + "</div>")

    p.append("<table class='r'><thead><tr><th>Datum</th><th>Radno vrijeme</th><th>Mirovanje</th><th>Pripravnost</th>"
             "<th>Rad</th><th>Upravljanje</th><th>km</th><th>Napomena</th></tr></thead><tbody>")
    for d in days:
        note = ''
        if d['drive'] > 600:
            note = "<span class='bad'>&gt;10 h</span>"
        elif d['drive'] > 540:
            note = "&gt;9 h"
        p.append(f"<tr><td>{dname(d['date'])} {dstr(d['date'])}</td><td>{fmt(d['radno'])}</td><td>{fmt(d['rest'])}</td>"
                 f"<td>{fmt(d['availC'])}</td><td>{fmt(d['work'])}</td><td>{fmt(d['drive'])}</td><td>{d['km'] or ''}</td><td>{note}</td></tr>")
    p.append(f"<tr class='tot'><td>Zbir</td><td>{fmt(T('radno'))}</td><td>{fmt(T('rest'))}</td><td>{fmt(T('availC'))}</td>"
             f"<td>{fmt(T('work'))}</td><td>{fmt(T('drive'))}</td><td>{T('km')}</td><td></td></tr></tbody></table>")

    p.append("<h2>Pregled smjena</h2><table class='r'><thead><tr><th>Početak smjene</th><th>Kraj smjene</th><th>Trajanje</th>"
             "<th>Radno vrijeme</th><th>Mirovanje</th><th>Pripravnost</th><th>Rad</th><th>Upravljanje</th></tr></thead><tbody>")
    for s in shifts:
        p.append(f"<tr><td>{dtstr(s['start'])}</td><td style='text-align:left'>{dtstr(s['end'])}</td><td>{fmt(s['dur'])}</td>"
                 f"<td>{fmt(s['radno'])}</td><td>{fmt(s['rest'])}</td><td>{fmt(s['avail'])}</td><td>{fmt(s['work'])}</td><td>{fmt(s['drive'])}</td></tr>")
    S = lambda k: sum(s[k] for s in shifts)
    p.append(f"<tr class='tot'><td>Zbir</td><td></td><td>{fmt(S('dur'))}</td><td>{fmt(S('radno'))}</td><td>{fmt(S('rest'))}</td>"
             f"<td>{fmt(S('avail'))}</td><td>{fmt(S('work'))}</td><td>{fmt(S('drive'))}</td></tr></tbody></table>")

    p.append("<h2>Sedmični pregled</h2><table class='r'><thead><tr><th>Sedmica</th><th>Upravljanje</th><th>Rad</th>"
             "<th>Radno vrijeme</th><th>Aktivnih dana</th><th>Dana &gt;9 h</th><th>2 sedmice</th><th>Napomena</th></tr></thead><tbody>")
    for w in weeks:
        n = []
        if w['drive'] > 3360:
            n.append("&gt;56 h")
        if w['two'] > 5400:
            n.append("2 sedm. &gt;90 h")
        p.append(f"<tr><td>{dstr(w['mon'])} - {dstr(w['mon'] + TD(days=6))}</td><td>{fmt(w['drive'])}</td><td>{fmt(w['work'])}</td>"
                 f"<td>{fmt(w['radno'])}</td><td>{w['days']}</td><td>{w['long9']}</td><td>{fmt(w['two'])}</td>"
                 f"<td class='bad'>{', '.join(n)}</td></tr>")
    p.append("</tbody></table>")

    p.append("<h2>Prekršaji i upozorenja (EU 561/2006 / AETR - indikativno)</h2>")
    if viol:
        p.append("<table class='r'><thead><tr><th>Vrijeme</th><th>Nivo</th><th>Vrsta</th><th>Detalj</th></tr></thead><tbody>")
        for v in viol:
            cls = 'bad' if v['level'] == 'Prekršaj' else ('warn' if v['level'] == 'Upozorenje' else '')
            p.append(f"<tr><td>{dtstr(v['when'])}</td><td class='{cls}' style='text-align:left'>{v['level']}</td>"
                     f"<td style='text-align:left'>{_e(v['type'])}</td><td style='text-align:left'>{_e(v['detail'])}</td></tr>")
        p.append("</tbody></table>")
    else:
        p.append("<p>Nije pronađen nijedan prekršaj u odabranom periodu.</p>")

    veh = [v for v in card.vehicles if a <= v['first'].date() <= b]
    p.append("<h2>Korištena vozila</h2><table class='r'><thead><tr><th>Od</th><th>Do</th><th>Registracija</th><th>km početak</th>"
             "<th>km kraj</th><th>Pređeno km</th></tr></thead><tbody>")
    for v in veh:
        p.append(f"<tr><td>{dtstr(v['first'])}</td><td style='text-align:left'>{dtstr(v['last']) if v['last'] else ''}</td>"
                 f"<td style='text-align:left'>{_e(v['reg'] + (' / ' + v['vin'] if v.get('vin') else ''))}</td><td>{v['odo_b']}</td><td>{v['odo_e']}</td><td>{max(0, v['odo_e'] - v['odo_b'])}</td></tr>")
    p.append("</tbody></table>")

    pl = [x for x in card.places if a <= x['time'].date() <= b]
    p.append("<h2>Mjesta početka / kraja radnog dana</h2><table class='r'><thead><tr><th>Vrijeme</th><th>Tip</th><th>Država</th>"
             "<th>Regija</th><th>km</th><th>GNSS</th></tr></thead><tbody>")
    for x in pl:
        p.append(f"<tr><td>{dtstr(x['time'])}</td><td style='text-align:left'>{_e(x['type'])}</td><td>{x['country']}</td><td>{x['region']}</td><td>{x['odo']}</td><td style='text-align:left'>{_e(x.get('gnss', ''))}</td></tr>")
    p.append("</tbody></table>")

    ev = [x for x in card.events if a <= x['begin'].date() <= b]
    p.append("<h2>Događaji, greške, kontrole</h2><table class='r'><thead><tr><th>Vrsta</th><th>Tip</th><th>Početak</th><th>Kraj</th>"
             "<th>Vozilo</th></tr></thead><tbody>")
    for x in ev:
        p.append(f"<tr><td style='text-align:left'>{x['kind']}</td><td style='text-align:left'>{_e(x['type'])}</td><td>{dtstr(x['begin'])}</td>"
                 f"<td>{dtstr(x['end']) if x['end'] else ''}</td><td>{_e(x['veh'])}</td></tr>")
    p.append("</tbody></table>")

    ex = [x for x in card.extra if a <= x['time'].date() <= b]
    if ex:
        p.append("<h2>GNSS pozicije i jedinice vozila (G2)</h2><table class='r'><thead><tr><th>Vrsta</th><th>Vrijeme</th>"
                 "<th>Detalj</th></tr></thead><tbody>")
        for x in ex:
            p.append(f"<tr><td style='text-align:left'>{_e(x['kind'])}</td><td>{dtstr(x['time'])}</td>"
                     f"<td style='text-align:left'>{_e(x['detail'])}</td></tr>")
        p.append("</tbody></table>")

    if detail:
        p.append("<h2>Detaljan pregled aktivnosti po danima</h2>")
        for d in days:
            if not (d['drive'] or d['work'] or d['availC']):
                continue
            rows = [x for x in an.intervals_of_day(d['date']) if x['ins'] or x['act'] != 0]
            p.append(f"<div class='day'><b>{dname(d['date'])} {dstr(d['date'])}</b> - upravljanje {fmt(d['drive'])}, rad {fmt(d['work'])}"
                     f"<table class='r'><thead><tr><th>Od</th><th>Do</th><th>Trajanje</th><th>Aktivnost</th><th>Kartica</th><th>Način</th></tr></thead><tbody>")
            for x in rows:
                p.append(f"<tr><td>{x['s'].strftime('%H:%M')}</td><td>{x['e'].strftime('%H:%M') if x['e'].hour or x['e'].minute else '24:00'}</td>"
                         f"<td>{fmt(mins(x['s'], x['e']))}</td><td style='text-align:left'>{ACT[x['act']]}</td>"
                         f"<td style='text-align:left'>{'umetnuta' if x['ins'] else 'nije umetnuta'}</td>"
                         f"<td style='text-align:left'>{'posada' if x['crew'] else 'solo'}</td></tr>")
            p.append("</tbody></table></div>")
            
    p.append("<h2>Struktura kartice</h2><pre style='font-size:10px; background:#f9f9f9; padding:8px; border:1px solid #ddd'>" + _e('\n'.join(card.summary_lines())) + "</pre>")
    p.append(foot + "</body></html>")
    return ''.join(p)

def find_browser():
    cands = []
    for env in ('ProgramFiles(x86)', 'ProgramFiles', 'LOCALAPPDATA'):
        base = os.environ.get(env)
        if base:
            cands += [os.path.join(base, r'Microsoft\Edge\Application\msedge.exe'),
                      os.path.join(base, r'Google\Chrome\Application\chrome.exe'),
                      os.path.join(base, r'Chromium\Application\chrome.exe')]
    for name in ('msedge', 'chrome', 'google-chrome', 'chromium', 'chromium-browser'):
        w = shutil.which(name)
        if w:
            cands.append(w)
    return next((c for c in cands if os.path.isfile(c)), None)

def html_to_pdf(html_path, pdf_path, browser=None, timeout=90):
    from pathlib import Path
    browser = browser or find_browser()
    if not browser:
        return False, "Nije pronađen Microsoft Edge ni Google Chrome."
    prof = tempfile.mkdtemp(prefix='taho_pdf_')
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except OSError:
            return False, "PDF fajl je otvoren u drugom programu - zatvorite ga."
    cmd = [browser, '--headless', '--disable-gpu', '--no-first-run', f'--user-data-dir={prof}',
           '--no-pdf-header-footer', '--print-to-pdf-no-header', f'--print-to-pdf={os.path.abspath(pdf_path)}',
           Path(os.path.abspath(html_path)).as_uri()]
    try:
        subprocess.run(cmd, timeout=timeout, capture_output=True,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except Exception as e:
        return False, f"Pokretanje preglednika nije uspjelo: {e}"
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    if os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 500:
        return True, pdf_path
    return False, "Preglednik nije napravio PDF."

def write_csv(path_base, an, a, b):
    card = an.card
    def out(suffix, head, rows):
        with open(f"{path_base}_{suffix}.csv", 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f, delimiter=';')
            w.writerow(head)
            w.writerows(rows)
        return f"{path_base}_{suffix}.csv"

    files = [
        out('dnevni', ['Datum', 'Dan', 'Radno vrijeme', 'Mirovanje', 'Pripravnost', 'Rad', 'Upravljanje', 'km'],
            [[dstr(d['date']), dname(d['date']), fmt(d['radno']), fmt(d['rest']), fmt(d['availC']), fmt(d['work']),
              fmt(d['drive']), d['km']] for d in an.days_range(a, b)]),
        out('smjene', ['Početak', 'Kraj', 'Trajanje', 'Radno vrijeme', 'Mirovanje', 'Pripravnost', 'Rad', 'Upravljanje'],
            [[s['start'].strftime('%d.%m.%Y %H:%M'), s['end'].strftime('%d.%m.%Y %H:%M'), fmt(s['dur']), fmt(s['radno']),
              fmt(s['rest']), fmt(s['avail']), fmt(s['work']), fmt(s['drive'])] for s in an.shifts_range(a, b)]),
        out('sedmice', ['Sedmica od', 'Upravljanje', 'Rad', 'Radno vrijeme', 'Aktivnih dana', 'Dana >9h', '2 sedmice'],
            [[dstr(w['mon']), fmt(w['drive']), fmt(w['work']), fmt(w['radno']), w['days'], w['long9'], fmt(w['two'])]
             for w in an.weeks_range(a, b)]),
        out('prekrsaji', ['Vrijeme', 'Nivo', 'Vrsta', 'Detalj'],
            [[v['when'].strftime('%d.%m.%Y %H:%M'), v['level'], v['type'], v['detail']] for v in an.violations_range(a, b)]),
        out('vozila', ['Od', 'Do', 'Registracija', 'VIN', 'km početak', 'km kraj'],
            [[v['first'].strftime('%d.%m.%Y %H:%M'), v['last'].strftime('%d.%m.%Y %H:%M') if v['last'] else '', v['reg'],
              v.get('vin', ''), v['odo_b'], v['odo_e']] for v in card.vehicles if a <= v['first'].date() <= b]),
        out('mjesta', ['Vrijeme', 'Tip', 'Država', 'Regija', 'km', 'GNSS'],
            [[x['time'].strftime('%d.%m.%Y %H:%M'), x['type'], x['country'], x['region'], x['odo'], x.get('gnss', '')]
             for x in card.places if a <= x['time'].date() <= b]),
        out('dogadjaji', ['Vrsta', 'Tip', 'Početak', 'Kraj', 'Vozilo'],
            [[x['kind'], x['type'], x['begin'].strftime('%d.%m.%Y %H:%M'),
              x['end'].strftime('%d.%m.%Y %H:%M') if x['end'] else '', x['veh']]
             for x in card.events if a <= x['begin'].date() <= b])
    ]
    return files

# =====================================================================
#  GUI (Glavna aplikacija)
# =====================================================================
class App:
    TZ = {'UTC+1 (kao EVA)': 'fix1', 'Lokalno (CET/CEST)': 'local', 'UTC': 'utc'}

    def __init__(self, root):
        self.root = root
        root.title("TahoCard Studio Pro 4.0")
        root.geometry("1250x800")
        self.card = None
        self.an = None
        try:
            self.pcsc = PCSC()
        except Exception as e:
            self.pcsc = None
            self.pcsc_err = str(e)
        self._ui()
        self.refresh_readers()
        self.log("Dobrodošli u TahoCard Studio Pro. Spreman za rad.")

    def _ui(self):
        top = ttk.Frame(self.root, padding=6)
        top.pack(fill='x')
        ttk.Label(top, text="Čitač:").pack(side='left')
        self.reader_var = tk.StringVar()
        self.reader_cb = ttk.Combobox(top, textvariable=self.reader_var, width=34, state='readonly')
        self.reader_cb.pack(side='left', padx=4)
        ttk.Button(top, text="Osvježi", command=self.refresh_readers).pack(side='left')
        ttk.Label(top, text="  Generacija:").pack(side='left')
        self.gen_var = tk.StringVar(value='Auto')
        ttk.Combobox(top, textvariable=self.gen_var, values=['Auto', 'G1', 'G2'], width=6, state='readonly').pack(side='left', padx=4)
        
        ttk.Button(top, text="1. Očitaj karticu", command=self.read_card).pack(side='left', padx=(12, 3))
        ttk.Button(top, text="2. Snimi .DDD", command=self.save_ddd).pack(side='left', padx=3)
        ttk.Button(top, text="3. Otvori .DDD", command=self.open_ddd).pack(side='left', padx=3)
        ttk.Button(top, text="4. HTML izvještaj", command=self.export_html).pack(side='left', padx=3)
        ttk.Button(top, text="5. CSV (Excel)", command=self.export_csv).pack(side='left', padx=3)
        ttk.Button(top, text="6. PDF (A4)", command=self.export_pdf).pack(side='left', padx=3)
        ttk.Button(top, text="Čišćenje kartice", command=self.clear_card_action).pack(side='left', padx=8)

        opt = ttk.LabelFrame(self.root, text=" Opcije i prikaz ", padding=(8, 4))
        opt.pack(fill='x', padx=6, pady=(2, 4))
        self.from_var, self.to_var = tk.StringVar(), tk.StringVar()
        self.days_var = tk.StringVar(value='90')
        self.tz_var = tk.StringVar(value='UTC+1 (kao EVA)')
        self.firm_var = tk.StringVar()
        self.empty_var = tk.BooleanVar(value=False)
        self.detail_var = tk.BooleanVar(value=True)
        self.orient_var = tk.StringVar(value='A4 položeno')

        r1 = ttk.Frame(opt)
        r1.pack(fill='x', pady=(0, 4))
        ttk.Label(r1, text="Period:", width=8).pack(side='left')
        ttk.Entry(r1, textvariable=self.from_var, width=11).pack(side='left')
        ttk.Label(r1, text=" - ").pack(side='left')
        ttk.Entry(r1, textvariable=self.to_var, width=11).pack(side='left')
        ttk.Label(r1, text="   Zadnjih").pack(side='left')
        ttk.Spinbox(r1, from_=1, to=366, textvariable=self.days_var, width=5).pack(side='left', padx=3)
        ttk.Label(r1, text="dana").pack(side='left')
        ttk.Button(r1, text="Postavi", command=self.set_default_period).pack(side='left', padx=(8, 3))
        ttk.Button(r1, text="Cijela kartica", command=self.set_full_period).pack(side='left', padx=3)

        r2 = ttk.Frame(opt)
        r2.pack(fill='x')
        ttk.Label(r2, text="Prikaz:", width=8).pack(side='left')
        ttk.Combobox(r2, textvariable=self.tz_var, values=list(self.TZ), width=18, state='readonly').pack(side='left')
        ttk.Checkbutton(r2, text="Prazni dani", variable=self.empty_var).pack(side='left', padx=(12, 0))
        ttk.Checkbutton(r2, text="Detalji u HTML-u", variable=self.detail_var).pack(side='left', padx=(12, 0))
        ttk.Label(r2, text="   Papir:").pack(side='left')
        ttk.Combobox(r2, textvariable=self.orient_var, values=['A4 položeno', 'A4 uspravno'], width=12,
                     state='readonly').pack(side='left', padx=3)
        ttk.Label(r2, text="   Naziv Firme:").pack(side='left')
        ttk.Entry(r2, textvariable=self.firm_var, width=24).pack(side='left', padx=3)
        ttk.Button(r2, text="Primijeni izmjene", command=self.refresh).pack(side='right')

        self.info_var = tk.StringVar(value="Kartica nije očitana.")
        ttk.Label(self.root, textvariable=self.info_var, font=('Arial', 10, 'bold'), padding=(8, 4)).pack(fill='x')

        nb = ttk.Notebook(self.root)
        nb.pack(fill='both', expand=True, padx=6, pady=4)
        self.nb = nb
        R, L, C = 'e', 'w', 'center'
        
        self.t_day = self._tree(nb, "Zbir dnevnih aktivnosti", [
            ('d', 'Datum', 120, L), ('rv', 'Radno vrijeme', 95, R), ('mi', 'Mirovanje', 85, R), ('pr', 'Pripravnost', 85, R),
            ('ra', 'Rad', 70, R), ('up', 'Upravljanje', 90, R), ('km', 'km', 60, R), ('p', 'Prvi početak', 100, C),
            ('z', 'Zadnji kraj', 100, C), ('sm', 'Smjena', 55, C), ('n', 'Napomena', 120, L)])
        self.t_day.bind('<<TreeviewSelect>>', self.on_day_select)
        
        self.t_sh = self._tree(nb, "Pregled smjena", [
            ('s', 'Početak smjene', 150, L), ('e', 'Kraj smjene', 150, L), ('t', 'Trajanje', 80, R), ('rv', 'Radno vrijeme', 95, R),
            ('mi', 'Mirovanje', 85, R), ('pr', 'Pripravnost', 85, R), ('ra', 'Rad', 70, R), ('up', 'Upravljanje', 90, R)])
            
        self.t_wk = self._tree(nb, "Sedmice", [
            ('w', 'Sedmica', 190, L), ('up', 'Upravljanje', 95, R), ('ra', 'Rad', 80, R), ('rv', 'Radno vrijeme', 100, R),
            ('ad', 'Aktivnih dana', 95, R), ('l9', 'Dana >9h', 80, R), ('tw', '2 sedmice', 90, R), ('n', 'Napomena', 160, L)])
            
        self.t_vi = self._tree(nb, "Prekršaji", [
            ('t', 'Vrijeme', 150, L), ('l', 'Nivo', 90, L), ('v', 'Vrsta', 200, L), ('d', 'Detalj', 480, L)])
            
        self._day_tab(nb)
        
        self.t_ve = self._tree(nb, "Vozila", [
            ('a', 'Od', 150, L), ('b', 'Do', 150, L), ('r', 'Registracija', 130, L), ('o1', 'km početak', 90, R),
            ('o2', 'km kraj', 90, R), ('km', 'Pređeno km', 90, R), ('vin', 'VIN', 150, L)])
            
        self.t_pl = self._tree(nb, "Mjesta", [
            ('t', 'Vrijeme', 150, L), ('ty', 'Tip', 200, L), ('c', 'Država', 80, C), ('r', 'Regija', 70, C), ('o', 'km', 90, R), ('g', 'GNSS (lat, lon)', 190, L)])
            
        self.t_ev = self._tree(nb, "Događaji i greške", [
            ('k', 'Vrsta', 100, L), ('ty', 'Tip', 280, L), ('b', 'Početak', 150, L), ('e', 'Kraj', 150, L), ('v', 'Vozilo', 130, L)])
            
        self.t_ex = self._tree(nb, "GNSS i VU", [
            ('k', 'Vrsta', 120, L), ('t', 'Vrijeme', 150, L), ('d', 'Detalj', 520, L)])
            
        kf = ttk.Frame(nb)
        nb.add(kf, text="Kartica")
        self.card_area = tk.Text(kf, font=('Consolas', 9), wrap='none')
        self.card_area.pack(fill='both', expand=True)
        
        fl = ttk.Frame(nb)
        nb.add(fl, text="Dnevnik")
        self.log_area = tk.Text(fl, font=('Consolas', 9), height=10)
        self.log_area.pack(fill='both', expand=True)

    def _tree(self, nb, title, cols):
        fr = ttk.Frame(nb)
        nb.add(fr, text=title)
        t = ttk.Treeview(fr, columns=[c[0] for c in cols], show='headings')
        for cid, h, w, a in cols:
            t.heading(cid, text=h)
            t.column(cid, width=w, anchor=a)
        vs = ttk.Scrollbar(fr, orient='vertical', command=t.yview)
        t.configure(yscrollcommand=vs.set)
        t.pack(side='left', fill='both', expand=True)
        vs.pack(side='right', fill='y')
        t.tag_configure('odd', background='#eeeeee')
        t.tag_configure('bad', foreground='#b00020')
        t.tag_configure('warn', foreground='#b36b00')
        t.tag_configure('tot', font=('Arial', 9, 'bold'))
        return t

    def _day_tab(self, nb):
        fr = ttk.Frame(nb)
        nb.add(fr, text="Detalj dana (Grafikon)")
        self.day_title = tk.StringVar(value="Odaberite dan u tabeli 'Zbir dnevnih aktivnosti'.")
        ttk.Label(fr, textvariable=self.day_title, font=('Arial', 11, 'bold')).pack(anchor='w', padx=8, pady=4)
        self.canvas = tk.Canvas(fr, height=110, bg='white', highlightthickness=1, highlightbackground='#ccc')
        self.canvas.pack(fill='x', padx=8)
        lg = ttk.Frame(fr)
        lg.pack(anchor='w', padx=8, pady=3)
        for a, txt in ((3, 'Upravljanje'), (2, 'Rad'), (1, 'Pripravnost'), (0, 'Odmor')):
            tk.Label(lg, bg=ACT_COL[a], width=2).pack(side='left')
            ttk.Label(lg, text=txt + '  ').pack(side='left')
        tk.Label(lg, bg='#dddddd', width=2).pack(side='left')
        ttk.Label(lg, text='Kartica nije umetnuta').pack(side='left')
        inner = ttk.Frame(fr)
        inner.pack(fill='both', expand=True)
        cols = [('s', 'Od', 80, 'center'), ('e', 'Do', 80, 'center'), ('t', 'Trajanje', 80, 'e'), ('a', 'Aktivnost', 140, 'w'),
                ('k', 'Kartica', 120, 'w'), ('m', 'Način', 80, 'w')]
        self.t_dd = ttk.Treeview(inner, columns=[c[0] for c in cols], show='headings')
        for cid, h, w, a in cols:
            self.t_dd.heading(cid, text=h)
            self.t_dd.column(cid, width=w, anchor=a)
        self.t_dd.pack(fill='both', expand=True, padx=8, pady=4)

    def log(self, m):
        self.log_area.insert('end', f"[{dt.datetime.now().strftime('%H:%M:%S')}] {m}\n")
        self.log_area.see('end')
        self.root.update_idletasks()

    def tzmode(self):
        return self.TZ[self.tz_var.get()]

    def refresh_readers(self):
        if not self.pcsc:
            self.log(f"PC/SC nije dostupan: {getattr(self, 'pcsc_err', '')}")
            return
        r = self.pcsc.readers()
        self.reader_cb['values'] = r
        if r:
            self.reader_var.set(r[0])
        self.log(f"Pronađeno čitača: {len(r)}")

    def read_card(self):
        if not self.pcsc or not self.reader_var.get():
            messagebox.showerror("Greška", "Čitač nije dostupan.")
            return
        try:
            self.log("--- Očitavanje kartice (Vozač / Firma) ---")
            self.root.config(cursor='watch')
            self.pcsc.connect(self.reader_var.get())
            recs = read_card_records(self.pcsc, self.gen_var.get(), self.log)
            card = CardData.from_records(recs)
            card.source = 'kartica'
            self.load_card(card)
            messagebox.showinfo("Gotovo", f"Kartica očitana.\nVozač/Vlasnik: {card.name}\nDnevnih zapisa: {len(card.days)}")
        except Exception as e:
            self.log(f"GREŠKA: {e}")
            messagebox.showerror("Greška", str(e))
        finally:
            self.root.config(cursor='')
            if self.pcsc:
                self.pcsc.disconnect()

    def clear_card_action(self):
        if not self.pcsc or not self.reader_var.get():
            messagebox.showerror("Greška", "Čitač nije dostupan.")
            return
        if not messagebox.askyesno("Sigurnosna potvrda", "Ova opcija šalje reset/clear signal kartici.\nDa li ste sigurni da želite nastaviti?"):
            return
        try:
            self.pcsc.connect(self.reader_var.get())
            ok, msg = self.pcsc.clear_card()
            if ok:
                messagebox.showinfo("Uspješno", msg)
                self.log(f"Čišćenje: {msg}")
            else:
                messagebox.showerror("Greška", msg)
                self.log(f"Greška kod čišćenja: {msg}")
        except Exception as e:
            messagebox.showerror("Greška", str(e))
        finally:
            if self.pcsc:
                self.pcsc.disconnect()

    def open_ddd(self):
        path = filedialog.askopenfilename(filetypes=[("DDD fajlovi", "*.ddd *.DDD *.c1b *.C1B"), ("Svi fajlovi", "*.*")])
        if not path:
            return
        try:
            with open(path, 'rb') as f:
                recs = parse_ddd(f.read())
            card = CardData.from_records(recs)
            card.source = os.path.basename(path)
            self.load_card(card)
            self.log(f"Učitan {path}")
        except Exception as e:
            messagebox.showerror("Greška", str(e))

    def save_ddd(self):
        if not self.card or not self.card.records:
            messagebox.showwarning("Nema podataka", "Prvo očitajte karticu.")
            return
        nm = f"{self.card.number or 'KARTICA'}_{dt.datetime.now().strftime('%Y%m%d_%H%M')}.ddd"
        path = filedialog.asksaveasfilename(defaultextension='.ddd', initialfile=nm, filetypes=[("DDD fajl", "*.ddd")])
        if path:
            with open(path, 'wb') as f:
                f.write(build_ddd(self.card.records))
            self.log(f"Snimljeno: {path}")
            messagebox.showinfo("Snimljeno", f"{path}")

    def load_card(self, card):
        self.card = card
        self.info_var.set(f"Ime: {card.name or '-'}   |   Kartica: {card.number or '-'} (G{card.gen})   |   "
                          f"Važi do: {dstr(card.expiry) if card.expiry else '-'}   |   Izvor: {card.source}")
        self.set_default_period()
        self.log_diagnostics()

    def log_diagnostics(self):
        c = self.card
        self.card_area.delete('1.0', 'end')
        self.card_area.insert('1.0', '\n'.join(c.summary_lines()))
        self.log(f"Zapisi pročitani, intervali: {len(c.intervals)}")
        for w in c.warnings:
            self.log(f"UPOZORENJE: {w}")

    def set_full_period(self):
        if not self.card or not self.card.intervals:
            return
        an = Analysis(self.card, self.tzmode())
        self.from_var.set(dstr(min(an.D)))
        self.to_var.set(dstr(an.last_date()))
        self.refresh()

    def set_default_period(self):
        if not self.card:
            return
        an = Analysis(self.card, self.tzmode())
        end = an.last_date()
        try:
            n = max(1, int(self.days_var.get()))
        except ValueError:
            n = 90
        self.to_var.set(dstr(end))
        self.from_var.set(dstr(end - TD(days=n - 1)))
        self.refresh()

    def period(self):
        return parse_date(self.from_var.get()), parse_date(self.to_var.get())

    def refresh(self):
        if not self.card:
            return
        try:
            a, b = self.period()
        except ValueError:
            messagebox.showerror("Greška", "Datum unesite u obliku dd.mm.gggg")
            return
        self.an = an = Analysis(self.card, self.tzmode())
        for t in (self.t_day, self.t_sh, self.t_wk, self.t_vi, self.t_ve, self.t_pl, self.t_ev, self.t_ex):
            t.delete(*t.get_children())

        def put(t, vals, i, tag=None):
            tags = ('odd',) if i % 2 else ()
            if tag:
                tags += (tag,)
            t.insert('', 'end', values=vals, tags=tags)

        days = an.days_range(a, b)
        shown = [d for d in days if self.empty_var.get() or d['drive'] or d['work'] or d['radno']]
        for i, d in enumerate(shown):
            note = '>10 h' if d['drive'] > 600 else ('>9 h' if d['drive'] > 540 else '')
            put(self.t_day, (f"{dname(d['date'])} {dstr(d['date'])}", fmt(d['radno']), fmt(d['rest']), fmt(d['availC']),
                             fmt(d['work']), fmt(d['drive']), d['km'] or '',
                             d['first'].strftime('%H:%M') if d['first'] else '', d['last'].strftime('%H:%M') if d['last'] else '',
                             d['nshift'] or '', note), i, 'bad' if d['drive'] > 600 else ('warn' if d['drive'] > 540 else None))
        T = lambda k: sum(d[k] for d in days)
        self.t_day.insert('', 'end', iid='total', tags=('tot',), values=('Zbir', fmt(T('radno')), fmt(T('rest')), fmt(T('availC')),
                                                                       fmt(T('work')), fmt(T('drive')), T('km'), '', '', '', ''))
        sh = an.shifts_range(a, b)
        for i, s in enumerate(sh):
            put(self.t_sh, (dtstr(s['start']), dtstr(s['end']), fmt(s['dur']), fmt(s['radno']), fmt(s['rest']),
                            fmt(s['avail']), fmt(s['work']), fmt(s['drive'])), i)
        S = lambda k: sum(s[k] for s in sh)
        self.t_sh.insert('', 'end', tags=('tot',), values=('Zbir', '', fmt(S('dur')), fmt(S('radno')), fmt(S('rest')),
                                                          fmt(S('avail')), fmt(S('work')), fmt(S('drive'))))
        for i, w in enumerate(an.weeks_range(a, b)):
            n = []
            if w['drive'] > 3360:
                n.append('>56 h')
            if w['two'] > 5400:
                n.append('2 sedm. >90 h')
            put(self.t_wk, (f"{dstr(w['mon'])} - {dstr(w['mon'] + TD(days=6))}", fmt(w['drive']), fmt(w['work']), fmt(w['radno']),
                            w['days'], w['long9'], fmt(w['two']), ', '.join(n)), i, 'bad' if n else None)
        for i, v in enumerate(an.violations_range(a, b)):
            put(self.t_vi, (dtstr(v['when']), v['level'], v['type'], v['detail']), i,
                'bad' if v['level'] == 'Prekršaj' else ('warn' if v['level'] == 'Upozorenje' else None))
        for i, v in enumerate([v for v in self.card.vehicles if a <= v['first'].date() <= b]):
            put(self.t_ve, (dtstr(v['first']), dtstr(v['last']) if v['last'] else '', v['reg'], v['odo_b'], v['odo_e'],
                            max(0, v['odo_e'] - v['odo_b']), v.get('vin', '')), i)
        for i, x in enumerate([x for x in self.card.places if a <= x['time'].date() <= b]):
            put(self.t_pl, (dtstr(x['time']), x['type'], x['country'], x['region'], x['odo'], x.get('gnss', '')), i)
        for i, x in enumerate([x for x in self.card.events if a <= x['begin'].date() <= b]):
            put(self.t_ev, (x['kind'], x['type'], dtstr(x['begin']), dtstr(x['end']) if x['end'] else '', x['veh']), i)
        for i, x in enumerate([x for x in self.card.extra if a <= x['time'].date() <= b]):
            put(self.t_ex, (x['kind'], dtstr(x['time']), x['detail']), i)

    def on_day_select(self, _):
        sel = self.t_day.selection()
        if not sel or sel[0] == 'total' or not self.an:
            return
        txt = self.t_day.item(sel[0], 'values')[0]
        try:
            d = parse_date(txt.split()[-1])
        except Exception:
            return
        self.show_day(d)

    def show_day(self, d):
        r = self.an.day(d)
        self.day_title.set(f"{dname(d)} {dstr(d)}  |  upravljanje {fmt(r['drive'])}  rad {fmt(r['work'])}  "
                           f"radno vrijeme {fmt(r['radno'])}  mirovanje {fmt(r['rest'])}  km {r['km']}")
        c = self.canvas
        c.delete('all')
        c.update_idletasks()
        W = max(c.winfo_width(), 900)
        m = 30
        scale = (W - 2 * m) / 1440
        rows = self.an.intervals_of_day(d)
        for x in rows:
            x0 = m + (x['s'] - dt.datetime.combine(d, dt.time())).total_seconds() / 60 * scale
            x1 = m + (x['e'] - dt.datetime.combine(d, dt.time())).total_seconds() / 60 * scale
            top = {3: 20, 2: 40, 1: 60, 0: 80}[x['act']]
            col = ACT_COL[x['act']] if x['ins'] else ('#dddddd' if x['act'] == 0 else ACT_COL[x['act']])
            c.create_rectangle(x0, top, max(x1, x0 + 1), top + 18, fill=col, outline='')
        for h in range(0, 25, 2):
            xx = m + h * 60 * scale
            c.create_line(xx, 14, xx, 102, fill='#e5e5e5')
            c.create_text(xx, 8, text=str(h), font=('Arial', 8))
        for lab, y in (('Upr.', 29), ('Rad', 49), ('Prip.', 69), ('Odmor', 89)):
            c.create_text(4, y, text=lab, anchor='w', font=('Arial', 7))
        self.t_dd.delete(*self.t_dd.get_children())
        for x in rows:
            self.t_dd.insert('', 'end', values=(x['s'].strftime('%H:%M'),
                                                 x['e'].strftime('%H:%M') if (x['e'].hour or x['e'].minute) else '24:00',
                                                 fmt(mins(x['s'], x['e'])), ACT[x['act']],
                                                 'umetnuta' if x['ins'] else 'nije umetnuta', 'posada' if x['crew'] else 'solo'))

    def _ready(self):
        if not self.card or not self.an:
            messagebox.showwarning("Nema podataka", "Prvo očitajte karticu.")
            return None
        try:
            return self.period()
        except ValueError:
            messagebox.showerror("Greška", "Neispravan datum.")
            return None

    def _html(self, p):
        orient = 'portrait' if 'uspravno' in self.orient_var.get() else 'landscape'
        return build_html(self.card, self.an, p[0], p[1], self.firm_var.get(), self.detail_var.get(), orient)

    def export_pdf(self):
        p = self._ready()
        if not p:
            return
        nm = f"Izvjestaj_{(self.card.name or 'vozac').replace(' ', '_')}.pdf"
        path = filedialog.asksaveasfilename(defaultextension='.pdf', initialfile=nm, filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        self.root.config(cursor='watch')
        self.root.update_idletasks()
        tmp = os.path.join(tempfile.gettempdir(), 'taho_izvjestaj.html')
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                f.write(self._html(p))
            ok, msg = html_to_pdf(tmp, path)
        finally:
            self.root.config(cursor='')
        if ok:
            self.log(f"PDF snimljen: {path}")
            try:
                os.startfile(path)
            except Exception:
                pass
            return
        alt = os.path.splitext(path)[0] + '.html'
        shutil.copyfile(tmp, alt)
        messagebox.showwarning("PDF nije napravljen", f"{msg}\nSnimljen HTML: {alt}")
        try:
            os.startfile(alt)
        except Exception:
            pass

    def export_html(self):
        p = self._ready()
        if not p:
            return
        nm = f"Izvjestaj_{(self.card.name or 'vozac').replace(' ', '_')}.html"
        path = filedialog.asksaveasfilename(defaultextension='.html', initialfile=nm, filetypes=[("HTML", "*.html")])
        if not path:
            return
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self._html(p))
        self.log(f"HTML snimljen: {path}")
        try:
            os.startfile(path)
        except Exception:
            pass

    def export_csv(self):
        p = self._ready()
        if not p:
            return
        path = filedialog.asksaveasfilename(defaultextension='.csv', initialfile='izvjestaj', filetypes=[("CSV", "*.csv")])
        if path:
            base = path[:-4] if path.lower().endswith('.csv') else path
            files = write_csv(base, self.an, p[0], p[1])
            messagebox.showinfo("Snimljeno", "\n".join(files))

def main():
    if tk is None:
        sys.exit(1)
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == '__main__':
    main()