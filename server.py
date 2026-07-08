#!/usr/bin/env python3
import http.server
import json
import os
import socket
from urllib.parse import urlparse
import urllib.request

DATA_FILE = "prode_data.json"
USERS = ["Walter", "Luisina", "Tomy", "Ema", "Sergio"]

# Normalización de nombres de equipos a códigos internos
TEAM_MAP = {
    "mexico":"mx", "south africa":"za", "south korea":"kr",
    "czech republic":"cz", "uefa path d winner":"cz",
    "canada":"ca", "bosnia & herzegovina":"ba", "qatar":"qa", "switzerland":"ch",
    "uefa path a winner":"ba",
    "brazil":"br", "morocco":"ma", "haiti":"ht", "scotland":"sc",
    "usa":"us", "paraguay":"py", "australia":"au", "turkey":"tr",
    "uefa path c winner":"tr",
    "germany":"de", "curacao":"cw", "curaçao":"cw", "ivory coast":"ci", "ecuador":"ec",
    "netherlands":"nl", "japan":"jp", "uefa path b winner":"se", "tunisia":"tn",
    "belgium":"be", "egypt":"eg", "iran":"ir", "new zealand":"nz",
    "spain":"es", "cape verde":"cv", "saudi arabia":"sa", "uruguay":"uy",
    "france":"fr", "senegal":"sn", "iraq":"iq", "norway":"no",
    "argentina":"ar", "algeria":"dz", "austria":"at", "jordan":"jo",
    "portugal":"pt", "dr congo":"cd", "uzbekistan":"uz", "colombia":"co",
    "england":"eng", "croatia":"hr", "ghana":"gh", "panama":"pa",
}

# (cod_local, cod_visita) -> id partido en nuestro sistema
MATCH_BY_TEAMS = {
    ("mx","za"):"p1",  ("kr","cz"):"p2",  ("cz","za"):"p3",  ("mx","kr"):"p4",
    ("cz","mx"):"p5",  ("za","kr"):"p6",
    ("ca","ba"):"p7",  ("qa","ch"):"p8",  ("ch","ba"):"p9",  ("ca","qa"):"p10",
    ("ch","ca"):"p11", ("ba","qa"):"p12",
    ("br","ma"):"p13", ("ht","sc"):"p14", ("sc","ma"):"p15", ("br","ht"):"p16",
    ("sc","br"):"p17", ("ma","ht"):"p18",
    ("us","py"):"p19", ("au","tr"):"p20", ("us","au"):"p21", ("tr","py"):"p22",
    ("tr","us"):"p23", ("py","au"):"p24",
    ("de","cw"):"p25", ("ci","ec"):"p26", ("de","ci"):"p27", ("ec","cw"):"p28",
    ("ec","de"):"p29", ("cw","ci"):"p30",
    ("nl","jp"):"p31", ("se","tn"):"p32", ("nl","se"):"p33", ("tn","jp"):"p34",
    ("jp","se"):"p35", ("tn","nl"):"p36",
    ("be","eg"):"p37", ("ir","nz"):"p38", ("be","ir"):"p39", ("nz","eg"):"p40",
    ("eg","ir"):"p41", ("nz","be"):"p42",
    ("es","cv"):"p43", ("sa","uy"):"p44", ("es","sa"):"p45", ("uy","cv"):"p46",
    ("cv","sa"):"p47", ("uy","es"):"p48",
    ("fr","sn"):"p49", ("iq","no"):"p50", ("fr","iq"):"p51", ("no","sn"):"p52",
    ("no","fr"):"p53", ("sn","iq"):"p54",
    ("ar","dz"):"p55", ("at","jo"):"p56", ("ar","at"):"p57", ("jo","dz"):"p58",
    ("dz","at"):"p59", ("jo","ar"):"p60",
    ("pt","cd"):"p61", ("uz","co"):"p62", ("pt","uz"):"p63", ("co","cd"):"p64",
    ("co","pt"):"p65", ("cd","uz"):"p66",
    ("eng","hr"):"p67", ("gh","pa"):"p68", ("eng","gh"):"p69", ("pa","hr"):"p70",
    ("pa","eng"):"p71", ("hr","gh"):"p72",
    # 16avos
    ("za","ca"):"r1", ("br","jp"):"r2", ("nl","ma"):"r3", ("de","py"):"r4",
    ("fr","se"):"r5", ("dz","ch"):"r6", ("mx","ec"):"r7", ("cd","eng"):"r8",
    ("be","sn"):"r9", ("us","ba"):"r10", ("es","at"):"r11", ("pt","hr"):"r12",
    ("ci","no"):"r13", ("eg","au"):"r14", ("ar","cv"):"r15", ("co","gh"):"r16",
}

OPENFOOTBALL_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

# Bracket oficial FIFA 2026: cada octavo (o1-o8) se arma con los ganadores
# de estos dos partidos de 16avos. Confirmado contra el bracket oficial
# (M73-M96) y los horarios ya cargados.
BRACKET = {
    "o1": ("r1", "r3"),
    "o2": ("r4", "r5"),
    "o3": ("r2", "r13"),
    "o4": ("r7", "r8"),
    "o5": ("r12", "r11"),
    "o6": ("r10", "r9"),
    "o7": ("r15", "r14"),
    "o8": ("r6", "r16"),
}

PARTIDOS = [
  # ── GRUPO A ──
  {"id":"p1","g":"Grupo A","l":"México","lf":"🇲🇽","v":"Sudáfrica","vf":"🇿🇦","dt":"2026-06-11T16:00"},
  {"id":"p2","g":"Grupo A","l":"Corea del Sur","lf":"🇰🇷","v":"Chequia","vf":"🇨🇿","dt":"2026-06-11T23:00"},
  {"id":"p3","g":"Grupo A","l":"Chequia","lf":"🇨🇿","v":"Sudáfrica","vf":"🇿🇦","dt":"2026-06-18T13:00"},
  {"id":"p4","g":"Grupo A","l":"México","lf":"🇲🇽","v":"Corea del Sur","vf":"🇰🇷","dt":"2026-06-18T22:00"},
  {"id":"p5","g":"Grupo A","l":"Chequia","lf":"🇨🇿","v":"México","vf":"🇲🇽","dt":"2026-06-24T22:00"},
  {"id":"p6","g":"Grupo A","l":"Sudáfrica","lf":"🇿🇦","v":"Corea del Sur","vf":"🇰🇷","dt":"2026-06-24T22:00"},
  # ── GRUPO B ──
  {"id":"p7","g":"Grupo B","l":"Canadá","lf":"🇨🇦","v":"Bosnia y Herz.","vf":"🇧🇦","dt":"2026-06-12T16:00"},
  {"id":"p8","g":"Grupo B","l":"Qatar","lf":"🇶🇦","v":"Suiza","vf":"🇨🇭","dt":"2026-06-13T16:00"},
  {"id":"p9","g":"Grupo B","l":"Suiza","lf":"🇨🇭","v":"Bosnia y Herz.","vf":"🇧🇦","dt":"2026-06-18T16:00"},
  {"id":"p10","g":"Grupo B","l":"Canadá","lf":"🇨🇦","v":"Qatar","vf":"🇶🇦","dt":"2026-06-18T19:00"},
  {"id":"p11","g":"Grupo B","l":"Suiza","lf":"🇨🇭","v":"Canadá","vf":"🇨🇦","dt":"2026-06-24T16:00"},
  {"id":"p12","g":"Grupo B","l":"Bosnia y Herz.","lf":"🇧🇦","v":"Qatar","vf":"🇶🇦","dt":"2026-06-24T16:00"},
  # ── GRUPO C ──
  {"id":"p13","g":"Grupo C","l":"Brasil","lf":"🇧🇷","v":"Marruecos","vf":"🇲🇦","dt":"2026-06-13T19:00"},
  {"id":"p14","g":"Grupo C","l":"Haití","lf":"🇭🇹","v":"Escocia","vf":"🏴󠁧󠁢󠁳󠁣󠁴󠁿","dt":"2026-06-13T22:00"},
  {"id":"p15","g":"Grupo C","l":"Escocia","lf":"🏴󠁧󠁢󠁳󠁣󠁴󠁿","v":"Marruecos","vf":"🇲🇦","dt":"2026-06-19T19:00"},
  {"id":"p16","g":"Grupo C","l":"Brasil","lf":"🇧🇷","v":"Haití","vf":"🇭🇹","dt":"2026-06-19T21:30"},
  {"id":"p17","g":"Grupo C","l":"Escocia","lf":"🏴󠁧󠁢󠁳󠁣󠁴󠁿","v":"Brasil","vf":"🇧🇷","dt":"2026-06-24T19:00"},
  {"id":"p18","g":"Grupo C","l":"Marruecos","lf":"🇲🇦","v":"Haití","vf":"🇭🇹","dt":"2026-06-24T19:00"},
  # ── GRUPO D ──
  {"id":"p19","g":"Grupo D","l":"EE.UU.","lf":"🇺🇸","v":"Paraguay","vf":"🇵🇾","dt":"2026-06-12T22:00"},
  {"id":"p20","g":"Grupo D","l":"Australia","lf":"🇦🇺","v":"Turquía","vf":"🇹🇷","dt":"2026-06-14T01:00"},
  {"id":"p21","g":"Grupo D","l":"EE.UU.","lf":"🇺🇸","v":"Australia","vf":"🇦🇺","dt":"2026-06-19T16:00"},
  {"id":"p22","g":"Grupo D","l":"Turquía","lf":"🇹🇷","v":"Paraguay","vf":"🇵🇾","dt":"2026-06-20T02:00"},
  {"id":"p23","g":"Grupo D","l":"Turquía","lf":"🇹🇷","v":"EE.UU.","vf":"🇺🇸","dt":"2026-06-25T23:00"},
  {"id":"p24","g":"Grupo D","l":"Paraguay","lf":"🇵🇾","v":"Australia","vf":"🇦🇺","dt":"2026-06-25T23:00"},
  # ── GRUPO E ──
  {"id":"p25","g":"Grupo E","l":"Alemania","lf":"🇩🇪","v":"Curazao","vf":"🇨🇼","dt":"2026-06-14T14:00"},
  {"id":"p26","g":"Grupo E","l":"Costa de Marfil","lf":"🇨🇮","v":"Ecuador","vf":"🇪🇨","dt":"2026-06-14T20:00"},
  {"id":"p27","g":"Grupo E","l":"Alemania","lf":"🇩🇪","v":"Costa de Marfil","vf":"🇨🇮","dt":"2026-06-20T17:00"},
  {"id":"p28","g":"Grupo E","l":"Ecuador","lf":"🇪🇨","v":"Curazao","vf":"🇨🇼","dt":"2026-06-20T21:00"},
  {"id":"p29","g":"Grupo E","l":"Ecuador","lf":"🇪🇨","v":"Alemania","vf":"🇩🇪","dt":"2026-06-25T17:00"},
  {"id":"p30","g":"Grupo E","l":"Curazao","lf":"🇨🇼","v":"Costa de Marfil","vf":"🇨🇮","dt":"2026-06-25T17:00"},
  # ── GRUPO F ──
  {"id":"p31","g":"Grupo F","l":"Países Bajos","lf":"🇳🇱","v":"Japón","vf":"🇯🇵","dt":"2026-06-14T17:00"},
  {"id":"p32","g":"Grupo F","l":"Suecia","lf":"🇸🇪","v":"Túnez","vf":"🇹🇳","dt":"2026-06-14T23:00"},
  {"id":"p33","g":"Grupo F","l":"Países Bajos","lf":"🇳🇱","v":"Suecia","vf":"🇸🇪","dt":"2026-06-20T14:00"},
  {"id":"p34","g":"Grupo F","l":"Túnez","lf":"🇹🇳","v":"Japón","vf":"🇯🇵","dt":"2026-06-21T01:00"},
  {"id":"p35","g":"Grupo F","l":"Japón","lf":"🇯🇵","v":"Suecia","vf":"🇸🇪","dt":"2026-06-25T20:00"},
  {"id":"p36","g":"Grupo F","l":"Túnez","lf":"🇹🇳","v":"Países Bajos","vf":"🇳🇱","dt":"2026-06-25T20:00"},
  # ── GRUPO G ──
  {"id":"p37","g":"Grupo G","l":"Bélgica","lf":"🇧🇪","v":"Egipto","vf":"🇪🇬","dt":"2026-06-15T16:00"},
  {"id":"p38","g":"Grupo G","l":"Irán","lf":"🇮🇷","v":"Nueva Zelanda","vf":"🇳🇿","dt":"2026-06-15T22:00"},
  {"id":"p39","g":"Grupo G","l":"Bélgica","lf":"🇧🇪","v":"Irán","vf":"🇮🇷","dt":"2026-06-21T16:00"},
  {"id":"p40","g":"Grupo G","l":"Nueva Zelanda","lf":"🇳🇿","v":"Egipto","vf":"🇪🇬","dt":"2026-06-21T22:00"},
  {"id":"p41","g":"Grupo G","l":"Egipto","lf":"🇪🇬","v":"Irán","vf":"🇮🇷","dt":"2026-06-27T02:00"},
  {"id":"p42","g":"Grupo G","l":"Nueva Zelanda","lf":"🇳🇿","v":"Bélgica","vf":"🇧🇪","dt":"2026-06-27T02:00"},
  # ── GRUPO H ──
  {"id":"p43","g":"Grupo H","l":"España","lf":"🇪🇸","v":"Cabo Verde","vf":"🇨🇻","dt":"2026-06-15T13:00"},
  {"id":"p44","g":"Grupo H","l":"Arabia Saudí","lf":"🇸🇦","v":"Uruguay","vf":"🇺🇾","dt":"2026-06-15T19:00"},
  {"id":"p45","g":"Grupo H","l":"España","lf":"🇪🇸","v":"Arabia Saudí","vf":"🇸🇦","dt":"2026-06-21T13:00"},
  {"id":"p46","g":"Grupo H","l":"Uruguay","lf":"🇺🇾","v":"Cabo Verde","vf":"🇨🇻","dt":"2026-06-21T19:00"},
  {"id":"p47","g":"Grupo H","l":"Cabo Verde","lf":"🇨🇻","v":"Arabia Saudí","vf":"🇸🇦","dt":"2026-06-26T21:00"},
  {"id":"p48","g":"Grupo H","l":"Uruguay","lf":"🇺🇾","v":"España","vf":"🇪🇸","dt":"2026-06-26T21:00"},
  # ── GRUPO I ──
  {"id":"p49","g":"Grupo I","l":"Francia","lf":"🇫🇷","v":"Senegal","vf":"🇸🇳","dt":"2026-06-16T16:00"},
  {"id":"p50","g":"Grupo I","l":"Irak","lf":"🇮🇶","v":"Noruega","vf":"🇳🇴","dt":"2026-06-16T19:00"},
  {"id":"p51","g":"Grupo I","l":"Francia","lf":"🇫🇷","v":"Irak","vf":"🇮🇶","dt":"2026-06-22T18:00"},
  {"id":"p52","g":"Grupo I","l":"Noruega","lf":"🇳🇴","v":"Senegal","vf":"🇸🇳","dt":"2026-06-22T21:00"},
  {"id":"p53","g":"Grupo I","l":"Noruega","lf":"🇳🇴","v":"Francia","vf":"🇫🇷","dt":"2026-06-26T16:00"},
  {"id":"p54","g":"Grupo I","l":"Senegal","lf":"🇸🇳","v":"Irak","vf":"🇮🇶","dt":"2026-06-26T16:00"},
  # ── GRUPO J ──
  {"id":"p55","g":"Grupo J","l":"Argentina","lf":"🇦🇷","v":"Argelia","vf":"🇩🇿","dt":"2026-06-16T22:00"},
  {"id":"p56","g":"Grupo J","l":"Austria","lf":"🇦🇹","v":"Jordania","vf":"🇯🇴","dt":"2026-06-17T01:00"},
  {"id":"p57","g":"Grupo J","l":"Argentina","lf":"🇦🇷","v":"Austria","vf":"🇦🇹","dt":"2026-06-22T14:00"},
  {"id":"p58","g":"Grupo J","l":"Jordania","lf":"🇯🇴","v":"Argelia","vf":"🇩🇿","dt":"2026-06-23T02:00"},
  {"id":"p59","g":"Grupo J","l":"Argelia","lf":"🇩🇿","v":"Austria","vf":"🇦🇹","dt":"2026-06-27T23:00"},
  {"id":"p60","g":"Grupo J","l":"Jordania","lf":"🇯🇴","v":"Argentina","vf":"🇦🇷","dt":"2026-06-27T23:00"},
  # ── GRUPO K ──
  {"id":"p61","g":"Grupo K","l":"Portugal","lf":"🇵🇹","v":"DR Congo","vf":"🇨🇩","dt":"2026-06-17T14:00"},
  {"id":"p62","g":"Grupo K","l":"Uzbekistán","lf":"🇺🇿","v":"Colombia","vf":"🇨🇴","dt":"2026-06-17T23:00"},
  {"id":"p63","g":"Grupo K","l":"Portugal","lf":"🇵🇹","v":"Uzbekistán","vf":"🇺🇿","dt":"2026-06-23T14:00"},
  {"id":"p64","g":"Grupo K","l":"Colombia","lf":"🇨🇴","v":"DR Congo","vf":"🇨🇩","dt":"2026-06-23T23:00"},
  {"id":"p65","g":"Grupo K","l":"Colombia","lf":"🇨🇴","v":"Portugal","vf":"🇵🇹","dt":"2026-06-27T20:30"},
  {"id":"p66","g":"Grupo K","l":"DR Congo","lf":"🇨🇩","v":"Uzbekistán","vf":"🇺🇿","dt":"2026-06-27T20:30"},
  # ── GRUPO L ──
  {"id":"p67","g":"Grupo L","l":"Inglaterra","lf":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","v":"Croacia","vf":"🇭🇷","dt":"2026-06-17T17:00"},
  {"id":"p68","g":"Grupo L","l":"Ghana","lf":"🇬🇭","v":"Panamá","vf":"🇵🇦","dt":"2026-06-17T20:00"},
  {"id":"p69","g":"Grupo L","l":"Inglaterra","lf":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","v":"Ghana","vf":"🇬🇭","dt":"2026-06-23T17:00"},
  {"id":"p70","g":"Grupo L","l":"Panamá","lf":"🇵🇦","v":"Croacia","vf":"🇭🇷","dt":"2026-06-23T20:00"},
  {"id":"p71","g":"Grupo L","l":"Panamá","lf":"🇵🇦","v":"Inglaterra","vf":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","dt":"2026-06-27T18:00"},
  {"id":"p72","g":"Grupo L","l":"Croacia","lf":"🇭🇷","v":"Ghana","vf":"🇬🇭","dt":"2026-06-27T18:00"},
  # ── 16AVOS ──
  {"id":"r1","g":"16avos","l":"Sudáfrica","lf":"🇿🇦","v":"Canadá","vf":"🇨🇦","dt":"2026-06-28T16:00"},
  {"id":"r2","g":"16avos","l":"Brasil","lf":"🇧🇷","v":"Japón","vf":"🇯🇵","dt":"2026-06-29T14:00"},
  {"id":"r3","g":"16avos","l":"Países Bajos","lf":"🇳🇱","v":"Marruecos","vf":"🇲🇦","dt":"2026-06-29T22:00"},
  {"id":"r4","g":"16avos","l":"Alemania","lf":"🇩🇪","v":"Paraguay","vf":"🇵🇾","dt":"2026-06-29T17:30"},
  {"id":"r5","g":"16avos","l":"Francia","lf":"🇫🇷","v":"Suecia","vf":"🇸🇪","dt":"2026-06-30T18:00"},
  {"id":"r6","g":"16avos","l":"Argelia","lf":"🇩🇿","v":"Suiza","vf":"🇨🇭","dt":"2026-07-03T00:00"},
  {"id":"r7","g":"16avos","l":"México","lf":"🇲🇽","v":"Ecuador","vf":"🇪🇨","dt":"2026-06-30T22:00"},
  {"id":"r8","g":"16avos","l":"Congo DR","lf":"🇨🇩","v":"Inglaterra","vf":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","dt":"2026-07-01T13:00"},
  {"id":"r9","g":"16avos","l":"Bélgica","lf":"🇧🇪","v":"Senegal","vf":"🇸🇳","dt":"2026-07-01T17:00"},
  {"id":"r10","g":"16avos","l":"EE.UU.","lf":"🇺🇸","v":"Bosnia y Herz.","vf":"🇧🇦","dt":"2026-07-01T21:00"},
  {"id":"r11","g":"16avos","l":"España","lf":"🇪🇸","v":"Austria","vf":"🇦🇹","dt":"2026-07-02T16:00"},
  {"id":"r12","g":"16avos","l":"Portugal","lf":"🇵🇹","v":"Croacia","vf":"🇭🇷","dt":"2026-07-02T20:00"},
  {"id":"r13","g":"16avos","l":"Costa de Marfil","lf":"🇨🇮","v":"Noruega","vf":"🇳🇴","dt":"2026-06-30T14:00"},
  {"id":"r14","g":"16avos","l":"Egipto","lf":"🇪🇬","v":"Australia","vf":"🇦🇺","dt":"2026-07-03T15:00"},
  {"id":"r15","g":"16avos","l":"Argentina","lf":"🇦🇷","v":"Cabo Verde","vf":"🇨🇻","dt":"2026-07-03T19:00"},
  {"id":"r16","g":"16avos","l":"Colombia","lf":"🇨🇴","v":"Ghana","vf":"🇬🇭","dt":"2026-07-03T22:30"},
  # ── OCTAVOS ──
  {"id":"o1","g":"Octavos","l":"Gan. r1","lf":"⚽","v":"Gan. r3","vf":"⚽","dt":"2026-07-04T14:00"},
  {"id":"o2","g":"Octavos","l":"Gan. r4","lf":"⚽","v":"Gan. r5","vf":"⚽","dt":"2026-07-04T18:00"},
  {"id":"o3","g":"Octavos","l":"Gan. r2","lf":"⚽","v":"Gan. r13","vf":"⚽","dt":"2026-07-05T17:00"},
  {"id":"o4","g":"Octavos","l":"Gan. r7","lf":"⚽","v":"Gan. r8","vf":"⚽","dt":"2026-07-05T21:00"},
  {"id":"o5","g":"Octavos","l":"Gan. r12","lf":"⚽","v":"Gan. r11","vf":"⚽","dt":"2026-07-06T16:00"},
  {"id":"o6","g":"Octavos","l":"Gan. r10","lf":"⚽","v":"Gan. r9","vf":"⚽","dt":"2026-07-06T21:00"},
  {"id":"o7","g":"Octavos","l":"Gan. r15","lf":"⚽","v":"Gan. r14","vf":"⚽","dt":"2026-07-07T13:00"},
  {"id":"o8","g":"Octavos","l":"Gan. r6","lf":"⚽","v":"Gan. r16","vf":"⚽","dt":"2026-07-07T17:00"},
  # ── CUARTOS ──
  {"id":"q1","g":"Cuartos","l":"Gan. Octavo 1","lf":"⚽","v":"Gan. Octavo 2","vf":"⚽","dt":"2026-07-09T17:00"},
  {"id":"q2","g":"Cuartos","l":"Gan. Octavo 3","lf":"⚽","v":"Gan. Octavo 4","vf":"⚽","dt":"2026-07-10T16:00"},
  {"id":"q3","g":"Cuartos","l":"Gan. Octavo 5","lf":"⚽","v":"Gan. Octavo 6","vf":"⚽","dt":"2026-07-10T16:00"},
  {"id":"q4","g":"Cuartos","l":"Gan. Octavo 7","lf":"⚽","v":"Gan. Octavo 8","vf":"⚽","dt":"2026-07-11T22:00"},
  # ── SEMIS ──
  {"id":"s1","g":"Semifinales","l":"Gan. Cuarto 1","lf":"⚽","v":"Gan. Cuarto 2","vf":"⚽","dt":"2026-07-14T16:00"},
  {"id":"s2","g":"Semifinales","l":"Gan. Cuarto 3","lf":"⚽","v":"Gan. Cuarto 4","vf":"⚽","dt":"2026-07-15T16:00"},
  # ── 3er PUESTO ──
  {"id":"t1","g":"Tercer puesto","l":"Per. Semi 1","lf":"⚽","v":"Per. Semi 2","vf":"⚽","dt":"2026-07-18T18:00"},
  # ── FINAL ──
  {"id":"f1","g":"Final","l":"Gan. Semi 1","lf":"🏆","v":"Gan. Semi 2","vf":"🏆","dt":"2026-07-19T16:00"},
]

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Prode Mundial 2026</title>
<style>
:root{--oro:#c9a227;--orl:#f0c94a;--bg:#0a1628;--bg2:#0f1f3d;--bg3:#162847;--tx:#e8edf5;--mt:#8a9ab5;--bd:rgba(255,255,255,0.1);--cd:rgba(255,255,255,0.05);--vd:#25a85e;--rj:#e74c3c;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:system-ui,sans-serif;background:var(--bg);color:var(--tx);min-height:100vh;}
.hdr{background:var(--bg2);border-bottom:2px solid var(--oro);padding:14px 16px;text-align:center;}
.hdr h1{font-size:22px;font-weight:800;color:var(--orl);letter-spacing:2px;}
.hdr p{font-size:10px;color:var(--mt);margin-top:2px;letter-spacing:1px;text-transform:uppercase;}
.nav{display:flex;border-bottom:1px solid var(--bd);background:var(--bg2);overflow-x:auto;scrollbar-width:none;}
.nav::-webkit-scrollbar{display:none;}
.nb{flex:1;min-width:72px;background:none;border:none;color:var(--mt);padding:10px 4px;font-size:10px;font-weight:700;cursor:pointer;border-bottom:2px solid transparent;transition:all .2s;white-space:nowrap;letter-spacing:.5px;text-transform:uppercase;font-family:inherit;}
.nb.active{color:var(--orl);border-bottom-color:var(--oro);background:rgba(201,162,39,.05);}
.nb:hover{color:var(--tx);}
.page{display:none;padding:12px;max-width:680px;margin:0 auto;}
.page.active{display:block;}
.stitle{font-size:16px;font-weight:800;color:var(--orl);margin-bottom:12px;padding-bottom:7px;border-bottom:1px solid var(--bd);letter-spacing:1px;text-transform:uppercase;}
input,select{width:100%;background:var(--bg3);border:1px solid var(--bd);border-radius:8px;color:var(--tx);padding:8px 11px;font-size:14px;font-family:inherit;outline:none;transition:border-color .2s;}
input:focus,select:focus{border-color:var(--oro);}
select option{background:var(--bg2);}

/* SAVE BAR — siempre visible arriba */
.save-bar{
  position:sticky;top:0;z-index:100;
  background:var(--vd);
  padding:10px 14px;
  display:flex;align-items:center;justify-content:space-between;
  gap:10px;
  border-radius:10px;
  margin-bottom:12px;
  box-shadow:0 4px 16px rgba(0,0,0,.4);
}
.save-bar .info{font-size:12px;color:rgba(255,255,255,.85);}
.save-bar .info strong{font-size:14px;color:#fff;}
.save-bar button{
  background:#fff;color:var(--vd);
  border:none;border-radius:7px;
  padding:8px 18px;font-size:13px;font-weight:800;
  cursor:pointer;font-family:inherit;white-space:nowrap;
  transition:all .2s;flex-shrink:0;
}
.save-bar button:hover{background:var(--orl);color:var(--bg);}
.save-bar.dirty{background:var(--rj);}
.save-bar.dirty button{color:var(--rj);}

.btn{background:var(--oro);color:var(--bg);border:none;border-radius:8px;padding:10px 18px;font-size:14px;font-weight:700;cursor:pointer;width:100%;font-family:inherit;transition:all .2s;margin-top:8px;}
.btn:hover{background:var(--orl);}
.btn2{background:transparent;color:var(--mt);border:1px solid var(--bd);}
.btn2:hover{background:var(--cd);color:var(--tx);}
.usel{display:flex;align-items:center;gap:10px;background:var(--bg3);border:1px solid var(--bd);border-radius:10px;padding:11px 13px;margin-bottom:14px;}
.usel select{width:auto;flex:1;padding:6px 10px;font-size:13px;}
.av{width:34px;height:34px;border-radius:50%;background:var(--oro);color:var(--bg);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:14px;flex-shrink:0;}
.sgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;}
.scard{background:var(--cd);border:1px solid var(--bd);border-radius:10px;padding:12px;text-align:center;}
.scard .val{font-size:22px;font-weight:800;color:var(--orl);}
.scard .lbl{font-size:10px;color:var(--mt);margin-top:2px;text-transform:uppercase;letter-spacing:.5px;}
.pbar{height:4px;background:var(--bd);border-radius:2px;overflow:hidden;margin-top:6px;}
.pfill{height:100%;background:var(--oro);border-radius:2px;transition:width .4s;}
.plbl{font-size:10px;color:var(--mt);margin-top:3px;}
.gh{background:var(--bg3);border-radius:8px 8px 0 0;padding:6px 12px;font-size:11px;font-weight:700;color:var(--oro);text-transform:uppercase;letter-spacing:1px;margin-top:12px;border:1px solid var(--bd);border-bottom:none;display:flex;align-items:center;justify-content:space-between;}
.gm{border:1px solid var(--bd);border-radius:0 0 8px 8px;overflow:hidden;}
.mr{display:grid;grid-template-columns:1fr auto 1fr;gap:6px;align-items:center;padding:9px 10px;border-bottom:1px solid var(--bd);background:var(--cd);position:relative;}
.mr:last-child{border-bottom:none;}
.mr.locked{opacity:.55;}
.mr.locked .si{background:rgba(255,255,255,.04);cursor:not-allowed;}
.mr .dt-badge{position:absolute;top:3px;right:8px;font-size:9px;color:var(--mt);}
.mr .lock-icon{position:absolute;top:3px;right:8px;font-size:10px;}
.tm{font-size:12px;font-weight:500;}
.tm.r{text-align:right;}
.sw{display:flex;align-items:center;gap:4px;}
.si{width:38px;text-align:center;font-size:16px;font-weight:700;padding:4px 2px;border-radius:5px;}
.ss{color:var(--mt);font-size:15px;font-weight:700;}
.rtable{width:100%;border-collapse:collapse;}
.rtable th{text-align:left;font-size:10px;color:var(--mt);text-transform:uppercase;letter-spacing:.5px;padding:8px 10px;border-bottom:1px solid var(--bd);}
.rtable td{padding:10px;border-bottom:1px solid var(--bd);font-size:13px;}
.rtable tr:last-child td{border-bottom:none;}
.rtable tr:hover td{background:var(--cd);}
.pos{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:50%;font-size:10px;font-weight:800;}
.p1{background:var(--oro);color:var(--bg);}
.p2{background:#9e9e9e;color:var(--bg);}
.p3{background:#8B6914;color:#fff;}
.pb{background:rgba(201,162,39,.15);color:var(--orl);padding:2px 8px;border-radius:10px;font-size:12px;font-weight:700;}
.sc{background:var(--cd);border:1px solid var(--bd);border-radius:12px;padding:16px;margin-bottom:10px;}
.sc h3{font-size:14px;font-weight:700;margin-bottom:5px;}
.sc p{font-size:12px;color:var(--mt);margin-bottom:12px;}
.bwa{background:#25D366;color:#fff;display:flex;align-items:center;justify-content:center;gap:8px;border-radius:10px;padding:12px;font-size:13px;font-weight:700;cursor:pointer;border:none;width:100%;font-family:inherit;transition:all .2s;}
.bwa:hover{background:#1fb855;}
.chip{display:inline-block;background:rgba(201,162,39,.1);color:var(--orl);border:1px solid rgba(201,162,39,.3);border-radius:20px;padding:2px 8px;font-size:10px;font-weight:600;margin-right:3px;}
.toast{position:fixed;bottom:14px;left:50%;transform:translateX(-50%) translateY(80px);background:var(--vd);color:#fff;padding:8px 16px;border-radius:8px;font-size:12px;font-weight:600;z-index:999;transition:transform .3s;pointer-events:none;}
.toast.show{transform:translateX(-50%) translateY(0);}
.spinner{display:inline-block;width:12px;height:12px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle;margin-right:5px;}
@keyframes spin{to{transform:rotate(360deg)}}
.fbadge{font-size:9px;font-weight:700;text-transform:uppercase;padding:1px 6px;border-radius:3px;margin-left:5px;}
.fg{background:rgba(45,158,90,.2);color:#4ecf82;}
.fe{background:rgba(201,162,39,.2);color:var(--orl);}
.res-badge{font-size:11px;font-weight:700;padding:2px 7px;border-radius:5px;margin-left:6px;}
.res-ok{background:rgba(45,158,90,.2);color:#4ecf82;}
.res-pending{background:rgba(255,255,255,.08);color:var(--mt);}
.auto-info{font-size:11px;color:var(--mt);background:rgba(255,255,255,.03);border:1px solid var(--bd);border-radius:6px;padding:7px 10px;margin-bottom:10px;display:flex;align-items:center;gap:6px;}
</style>
</head>
<body>
<div class="hdr">
  <h1>⚽ Prode Mundial 2026</h1>
  <p id="srv-ip">104 partidos · Grupos A–L + Eliminatorias</p>
</div>
<nav class="nav">
  <button class="nb active" onclick="showPage('inicio')">Inicio</button>
  <button class="nb" onclick="showPage('pronosticos')">Pronósticos</button>
  <button class="nb" onclick="showPage('resultados')">Resultados</button>
  <button class="nb" onclick="showPage('ranking')">Ranking</button>
  <button class="nb" onclick="showPage('compartir')">Compartir</button>
</nav>

<!-- INICIO -->
<div id="page-inicio" class="page active">
  <div class="stitle">Bienvenido/a</div>
  <div class="usel">
    <div class="av" id="av">?</div>
    <select id="sel" onchange="setUser(this.value)">
      <option value="">— ¿Quién sos? —</option>
    </select>
  </div>
  <div id="ini-stats" style="display:none">
    <div class="sgrid">
      <div class="scard"><div class="val" id="ini-p">0</div><div class="lbl">Pronósticos</div></div>
      <div class="scard"><div class="val" id="ini-pts">—</div><div class="lbl">Puntos</div></div>
    </div>
    <div class="pbar"><div class="pfill" id="pfill" style="width:0%"></div></div>
    <div class="plbl" id="plbl">0 de 104 partidos cargados</div>
    <button class="btn" onclick="showPage('pronosticos')">Cargar mis pronósticos ⚽</button>
    <button class="btn btn2" onclick="showPage('ranking')">Ver ranking 🏆</button>
  </div>
  <div id="ini-msg" style="text-align:center;padding:24px 0;color:var(--mt);font-size:13px;">Seleccioná tu nombre para empezar</div>
</div>

<!-- PRONÓSTICOS -->
<div id="page-pronosticos" class="page">
  <div class="stitle">Mis pronósticos</div>
  <div id="pw"></div>
</div>

<!-- RESULTADOS -->
<div id="page-resultados" class="page">
  <div class="stitle">Resultados</div>
  <div class="auto-info">
    🔄 <span id="auto-status">Los resultados se actualizan automáticamente desde internet.</span>
    <button onclick="fetchResultados(true)" style="margin-left:auto;background:var(--oro);color:var(--bg);border:none;border-radius:5px;padding:4px 10px;font-size:11px;font-weight:700;cursor:pointer;font-family:inherit;">Actualizar ahora</button>
  </div>
  <div id="rw"></div>
</div>

<!-- RANKING -->
<div id="page-ranking" class="page">
  <div class="stitle">Ranking</div>
  <div id="rkw"><p style="color:var(--mt);font-size:13px;text-align:center;padding:24px 0;">Cargando...</p></div>
</div>

<!-- COMPARTIR -->
<div id="page-compartir" class="page">
  <div class="stitle">Compartir</div>
  <div class="sc" style="text-align:center">
    <div style="font-size:36px;margin-bottom:8px;">📲</div>
    <h3>Invitá a tus compañeros</h3>
    <p>Compartí esta dirección por WhatsApp. Cualquiera en la misma red WiFi puede entrar.</p>
    <div style="background:var(--bg);border:1px solid var(--bd);border-radius:8px;padding:9px 12px;font-size:13px;font-weight:700;color:var(--orl);margin-bottom:12px;word-break:break-all;" id="share-url">Cargando...</div>
    <button class="bwa" onclick="shareWA()">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
      Compartir por WhatsApp
    </button>
  </div>
  <div class="sc">
    <h3 style="margin-bottom:8px;">Puntuación</h3>
    <div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--bd);font-size:12px;"><span>Resultado exacto</span><span class="chip">+3 pts</span></div>
    <div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--bd);font-size:12px;"><span>Ganador / empate correcto</span><span class="chip">+1 pt</span></div>
    <div style="display:flex;justify-content:space-between;padding:7px 0;font-size:12px;"><span>Incorrecto</span><span class="chip">0 pts</span></div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const USERS = __USERS__;
const PARTIDOS = __PARTIDOS__;
const TOTAL = PARTIDOS.length;
const PARTIDOS_BY_ID = {};
PARTIDOS.forEach(p => PARTIDOS_BY_ID[p.id] = p);

// Bracket oficial: cada octavo se arma con los ganadores de estos 2 partidos de 16avos
const BRACKET = {
  o1:['r1','r3'], o2:['r4','r5'], o3:['r2','r13'], o4:['r7','r8'],
  o5:['r12','r11'], o6:['r10','r9'], o7:['r15','r14'], o8:['r6','r16']
};

let currentUser = null;
let srvData = {pronos:{}, resultados:{}, penales:{}};
let pendingChanges = false;
let autoSaveTimer = null;

// ── Utilidades ──────────────────────────────────────────
function isLocked(dt) {
  if(!dt) return false;
  return new Date() >= new Date(dt);
}

function fmtDt(dt) {
  if(!dt) return '';
  const d = new Date(dt);
  const dias = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'];
  const meses = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
  return `${dias[d.getDay()]} ${d.getDate()} ${meses[d.getMonth()]} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
}

// Devuelve el equipo (nombre+bandera) ganador de un partido de 16avos,
// usando el resultado de 90'+alargue. Si terminó empatado, usa el dato
// de penales cargado manualmente. Si todavía no hay nada, devuelve null.
function getWinner(rid) {
  const p = PARTIDOS_BY_ID[rid];
  const r = srvData.resultados[rid];
  if(!p || !r || r.l==='' || r.v==='') return null;
  const rl = +r.l, rv = +r.v;
  if(rl > rv) return {nombre:p.l, bandera:p.lf};
  if(rv > rl) return {nombre:p.v, bandera:p.vf};
  // empate -> definicion por penales
  const lado = (srvData.penales||{})[rid];
  if(lado==='l') return {nombre:p.l, bandera:p.lf};
  if(lado==='v') return {nombre:p.v, bandera:p.vf};
  return null;
}

// Para un partido de Octavos (o1-o8), arma los nombres reales de los
// equipos a medida que se conocen los ganadores de 16avos. Si todavía
// no se sabe, muestra "Gan. EquipoA/EquipoB" en vez del id de partido.
function resolveTeams(p) {
  if(p.g !== 'Octavos' || !BRACKET[p.id]) return p;
  const [ridL, ridV] = BRACKET[p.id];
  const pl = PARTIDOS_BY_ID[ridL], pv = PARTIDOS_BY_ID[ridV];
  const winL = getWinner(ridL);
  const winV = getWinner(ridV);
  return {
    ...p,
    l: winL ? winL.nombre : `Gan. ${pl.l}/${pl.v}`,
    lf: winL ? winL.bandera : '⚽',
    v: winV ? winV.nombre : `Gan. ${pv.l}/${pv.v}`,
    vf: winV ? winV.bandera : '⚽'
  };
}

async function api(method, path, body) {
  const opts = {method, headers:{'Content-Type':'application/json'}};
  if(body) opts.body = JSON.stringify(body);
  const r = await fetch(path, opts);
  return r.json();
}

async function loadData() {
  srvData = await api('GET', '/api/data');
  USERS.forEach(u => { if(!srvData.pronos[u]) srvData.pronos[u]={}; });
  if(!srvData.resultados) srvData.resultados={};
  if(!srvData.penales) srvData.penales={};
  // Actualizar los partidos con los nombres reales resueltos por el servidor
  if(srvData.partidos_resueltos) {
    srvData.partidos_resueltos.forEach(p => { PARTIDOS_BY_ID[p.id] = p; });
    PARTIDOS.forEach((p,i) => {
      const r = PARTIDOS_BY_ID[p.id];
      if(r) { PARTIDOS[i] = r; }
    });
  }
}

// ── Navegación ──────────────────────────────────────────
function showPage(n) {
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nb').forEach(b=>b.classList.remove('active'));
  document.getElementById('page-'+n).classList.add('active');
  ['inicio','pronosticos','resultados','ranking','compartir'].forEach((p,i)=>{
    if(p===n) document.querySelectorAll('.nb')[i].classList.add('active');
  });
  if(n==='pronosticos') renderPronos();
  if(n==='resultados') renderResultados();
  if(n==='ranking') renderRanking();
}

// ── Usuario ─────────────────────────────────────────────
function initSel() {
  const s = document.getElementById('sel');
  s.innerHTML='<option value="">— ¿Quién sos? —</option>';
  USERS.forEach(u=>{const o=document.createElement('option');o.value=u;o.textContent=u;s.appendChild(o);});
}

function setUser(u) {
  currentUser = u||null;
  document.getElementById('av').textContent = currentUser ? currentUser[0] : '?';
  document.getElementById('ini-stats').style.display = currentUser ? 'block' : 'none';
  document.getElementById('ini-msg').style.display = currentUser ? 'none' : 'block';
  if(currentUser) refreshStats();
}

function calcPts(user) {
  const pr=srvData.pronos[user]||{}, re=srvData.resultados||{};
  if(!Object.keys(re).filter(k=>re[k].l!==''&&re[k].v!=='').length) return '—';
  let pts=0;
  Object.keys(re).forEach(id=>{
    const r=re[id],p=pr[id];
    if(!r||r.l===''||r.v==='') return;
    if(!p||p.l===''||p.v==='') return;
    const rl=+r.l,rv=+r.v,pl=+p.l,pv=+p.v;
    if(rl===pl&&rv===pv){pts+=3;return;}
    const rr=rl>rv?1:rl<rv?-1:0,pr2=pl>pv?1:pl<pv?-1:0;
    if(rr===pr2) pts+=1;
  });
  return pts;
}

function refreshStats() {
  if(!currentUser) return;
  const pr=srvData.pronos[currentUser]||{};
  const f=Object.keys(pr).filter(k=>pr[k].l!==''&&pr[k].v!=='').length;
  document.getElementById('ini-p').textContent=f+'/'+TOTAL;
  document.getElementById('ini-pts').textContent=calcPts(currentUser);
  document.getElementById('pfill').style.width=Math.round(f/TOTAL*100)+'%';
  document.getElementById('plbl').textContent=f+' de '+TOTAL+' partidos cargados';
}

// ── Save bar ─────────────────────────────────────────────
function showSaveBar(container) {
  let bar = document.getElementById('save-bar-pronos');
  if(!bar) {
    bar = document.createElement('div');
    bar.id = 'save-bar-pronos';
    bar.className = 'save-bar';
    bar.innerHTML = `<div class="info"><strong id="sb-user"></strong> — <span id="sb-count"></span></div><button onclick="savePronos()">💾 Guardar pronósticos</button>`;
    container.parentNode.insertBefore(bar, container);
  }
  document.getElementById('sb-user').textContent = currentUser || '';
  const pr=srvData.pronos[currentUser]||{};
  const f=Object.keys(pr).filter(k=>pr[k].l!==''&&pr[k].v!=='').length;
  document.getElementById('sb-count').textContent = f+' pronósticos cargados';
  bar.style.display='flex';
}

function updateSaveBar() {
  const bar = document.getElementById('save-bar-pronos');
  if(!bar) return;
  const pr=srvData.pronos[currentUser]||{};
  const f=Object.keys(pr).filter(k=>pr[k].l!==''&&pr[k].v!=='').length;
  document.getElementById('sb-count').textContent = f+' pronósticos cargados';
  if(pendingChanges) {
    bar.classList.add('dirty');
    bar.querySelector('button').textContent = '💾 Guardar (hay cambios sin guardar)';
  } else {
    bar.classList.remove('dirty');
    bar.querySelector('button').textContent = '💾 Guardar pronósticos';
  }
}

// ── Pronósticos ──────────────────────────────────────────
function renderPronos() {
  const wrap = document.getElementById('pw');
  if(!currentUser) {
    wrap.innerHTML='<p style="color:var(--mt);font-size:13px;text-align:center;padding:24px 0">Seleccioná tu nombre en Inicio primero</p>';
    return;
  }
  showSaveBar(wrap);
  const pr=srvData.pronos[currentUser]||{};
  const grupos=[...new Set(PARTIDOS.map(p=>p.g))];
  let html='';
  grupos.forEach(g=>{
    const esGrupo=g.startsWith('Grupo');
    const badge=esGrupo?'<span class="fbadge fg">Grupos</span>':'<span class="fbadge fe">Eliminatoria</span>';
    html+=`<div class="gh"><span>${g}${badge}</span></div><div class="gm">`;
    PARTIDOS.filter(p=>p.g===g).forEach(p0=>{
      const p=resolveTeams(p0);
      const locked=isLocked(p.dt);
      const vl=pr[p.id]?pr[p.id].l:'', vv=pr[p.id]?pr[p.id].v:'';
      const lockIcon=locked?'<span class="lock-icon">🔒</span>':`<span class="dt-badge">${fmtDt(p.dt)}</span>`;
      html+=`<div class="mr${locked?' locked':''}">
        ${lockIcon}
        <div class="tm">${p.lf} ${p.l}</div>
        <div class="sw">
          <input class="si" type="number" min="0" max="20" value="${vl}" placeholder="—" data-id="${p.id}" data-s="l" oninput="upP(this)" ${locked?'disabled':''}>
          <span class="ss">-</span>
          <input class="si" type="number" min="0" max="20" value="${vv}" placeholder="—" data-id="${p.id}" data-s="v" oninput="upP(this)" ${locked?'disabled':''}>
        </div>
        <div class="tm r">${p.v} ${p.vf}</div>
      </div>`;
    });
    html+='</div>';
  });
  wrap.innerHTML='';
  showSaveBar(wrap);
  const div=document.createElement('div');
  div.innerHTML=html;
  wrap.appendChild(div);
}

function upP(el) {
  if(!currentUser) return;
  const id=el.dataset.id,s=el.dataset.s;
  if(!srvData.pronos[currentUser][id]) srvData.pronos[currentUser][id]={l:'',v:''};
  srvData.pronos[currentUser][id][s]=el.value;
  pendingChanges=true;
  updateSaveBar();
  // Auto-guardar 3 segundos después de dejar de escribir
  clearTimeout(autoSaveTimer);
  autoSaveTimer=setTimeout(()=>savePronos(true),3000);
}

async function savePronos(silent=false) {
  if(!currentUser) return;
  clearTimeout(autoSaveTimer);
  // Actualizar UI de inmediato sin esperar al servidor
  pendingChanges=false;
  refreshStats();
  updateSaveBar();
  if(!silent) toast('Pronósticos guardados ✅');
  // Guardar en segundo plano
  api('POST','/api/pronos',{user:currentUser,pronos:srvData.pronos[currentUser]}).catch(()=>{
    // Si falla, marcar como pendiente de nuevo
    pendingChanges=true;
    updateSaveBar();
    toast('Error al guardar, reintentando...');
    autoSaveTimer=setTimeout(()=>savePronos(true),3000);
  });
}

// ── Resultados automáticos ───────────────────────────────
async function fetchResultados(manual=false) {
  document.getElementById('auto-status').textContent='Actualizando resultados...';
  try {
    const res = await api('GET', '/api/resultados-auto');
    if(res.ok) {
      srvData.resultados = res.resultados;
      renderResultados();
      const n = Object.keys(res.resultados).filter(k=>res.resultados[k].l!==''&&res.resultados[k].v!=='').length;
      document.getElementById('auto-status').textContent=`✅ ${n} resultados cargados · Última actualización: ${new Date().toLocaleTimeString('es-AR')}`;
      if(manual) toast('Resultados actualizados ✅');
    } else {
      document.getElementById('auto-status').textContent='⚠️ No se pudo conectar. Cargá los resultados manualmente abajo.';
      if(manual) toast('No se pudo conectar a la fuente de datos');
    }
  } catch(e) {
    document.getElementById('auto-status').textContent='⚠️ Sin conexión a internet. Cargá los resultados manualmente abajo.';
  }
}

function renderResultados() {
  const wrap=document.getElementById('rw'), re=srvData.resultados||{};
  const grupos=[...new Set(PARTIDOS.map(p=>p.g))];
  let html='';
  grupos.forEach(g=>{
    const esGrupo=g.startsWith('Grupo');
    const badge=esGrupo?'<span class="fbadge fg">Grupos</span>':'<span class="fbadge fe">Eliminatoria</span>';
    html+=`<div class="gh"><span>${g}${badge}</span></div><div class="gm">`;
    PARTIDOS.filter(p=>p.g===g).forEach(p0=>{
      const p=resolveTeams(p0);
      const played=isLocked(p.dt);
      const vl=re[p.id]?re[p.id].l:'', vv=re[p.id]?re[p.id].v:'';
      const hasResult=vl!==''&&vv!=='';
      const badge2=hasResult?`<span class="res-badge res-ok">${vl}-${vv}</span>`:(played?'<span class="res-badge res-pending">pendiente</span>':'');
      // Si es partido de eliminacion (no Grupo) y termino empatado, hay que
      // definir quien avanza por penales (eso no cambia el resultado/puntos,
      // solo sirve para armar el cruce siguiente del bracket).
      const esEliminacion = !p.g.startsWith('Grupo');
      const empatado = hasResult && (+vl === +vv);
      let penalesHtml = '';
      if(esEliminacion && empatado && BRACKET_SOURCE_IDS.has(p0.id)) {
        const ladoActual = (srvData.penales||{})[p0.id] || '';
        penalesHtml = `<div class="pen-sel" style="grid-column:1/-1;font-size:12px;color:var(--mt);margin-top:4px;">
          ⚖️ Empató, definió por penales:
          <select onchange="upPenal('${p0.id}', this.value)" style="margin-left:6px;">
            <option value="" ${ladoActual===''?'selected':''}>— elegir —</option>
            <option value="l" ${ladoActual==='l'?'selected':''}>${p0.l}</option>
            <option value="v" ${ladoActual==='v'?'selected':''}>${p0.v}</option>
          </select>
        </div>`;
      }
      html+=`<div class="mr">
        <span class="dt-badge">${fmtDt(p.dt)}</span>
        <div class="tm">${p.lf} ${p.l}</div>
        <div class="sw">
          <input class="si" type="number" min="0" max="20" value="${vl}" placeholder="—" data-id="${p.id}" data-s="l" oninput="upR(this)">
          <span class="ss">-</span>
          <input class="si" type="number" min="0" max="20" value="${vv}" placeholder="—" data-id="${p.id}" data-s="v" oninput="upR(this)">
        </div>
        <div class="tm r">${p.v} ${p.vf}</div>
        ${penalesHtml}
      </div>`;
    });
    html+='</div>';
  });
  wrap.innerHTML=html;
}

// Set con los ids de partidos de 16avos que alimentan algun octavo
// (todos: r1-r16). Sirve para saber donde mostrar el selector de penales.
const BRACKET_SOURCE_IDS = new Set(Object.values(BRACKET).flat());

async function upPenal(rid, lado) {
  if(!lado) return;
  srvData.penales = srvData.penales || {};
  srvData.penales[rid] = lado;
  await api('POST', '/api/penales', {rid, lado});
  toast('Definición por penales guardada ✅');
  renderResultados();
}

function upR(el) {
  const id=el.dataset.id,s=el.dataset.s;
  if(!srvData.resultados[id]) srvData.resultados[id]={l:'',v:''};
  srvData.resultados[id][s]=el.value;
  clearTimeout(autoSaveTimer);
  autoSaveTimer=setTimeout(async()=>{
    await api('POST','/api/resultados',{resultados:srvData.resultados});
    toast('Resultado guardado ✅');
  },1500);
}

// ── Ranking ──────────────────────────────────────────────
async function renderRanking() {
  await loadData();
  const wrap=document.getElementById('rkw');
  const ranked=USERS.map(u=>{
    const pr=srvData.pronos[u]||{};
    const f=Object.keys(pr).filter(k=>pr[k].l!==''&&pr[k].v!=='').length;
    return {name:u,pts:calcPts(u),f};
  }).sort((a,b)=>{const ap=typeof a.pts==='number'?a.pts:-1,bp=typeof b.pts==='number'?b.pts:-1;return bp-ap;});
  let html='<table class="rtable"><thead><tr><th>#</th><th>Jugador</th><th>Pronós.</th><th>Puntos</th></tr></thead><tbody>';
  ranked.forEach((u,i)=>{
    const m=i<3?`<span class="pos p${i+1}">${i+1}</span>`:`<span style="color:var(--mt);font-size:11px">${i+1}</span>`;
    const hl=u.name===currentUser?'background:rgba(201,162,39,.06)':'';
    html+=`<tr style="${hl}"><td>${m}</td><td style="font-weight:700">${u.name}${u.name===currentUser?' 👈':''}</td><td style="color:var(--mt);font-size:11px">${u.f}/${TOTAL}</td><td><span class="pb">${u.pts}</span></td></tr>`;
  });
  html+='</tbody></table>';
  wrap.innerHTML=html;
}

// ── Compartir ────────────────────────────────────────────
function shareWA() {
  const url=document.getElementById('share-url').textContent;
  const msg=`⚽ *Prode Mundial 2026* 🏆\n\n104 partidos · Grupos + Eliminatorias\n👉 ${url}\n\nParticipantes: ${USERS.join(', ')}`;
  window.open('https://wa.me/?text='+encodeURIComponent(msg),'_blank');
}

function toast(msg){
  const t=document.getElementById('toast');
  t.textContent=msg;t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),2500);
}

// ── Init ─────────────────────────────────────────────────
async function init() {
  await loadData();
  initSel();
  const ip=window.location.host;
  document.getElementById('srv-ip').textContent='Servidor: http://'+ip;
  document.getElementById('share-url').textContent='http://'+ip;
  // Actualizar resultados cada 5 minutos
  fetchResultados();
  setInterval(()=>fetchResultados(), 5*60*1000);
}
init();
</script>
</body>
</html>
"""

def normalize(name):
    return name.lower().strip()

def fetch_live_results():
    """Trae resultados de openfootball (actualizado diariamente, sin clave)."""
    try:
        req = urllib.request.Request(
            OPENFOOTBALL_URL,
            headers={"User-Agent": "ProdeMundial2026/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        resultados = {}
        for m in data.get("matches", []):
            score = m.get("score")
            if not score:
                continue
            t1 = normalize(m.get("team1", ""))
            t2 = normalize(m.get("team2", ""))
            c1 = TEAM_MAP.get(t1)
            c2 = TEAM_MAP.get(t2)
            if not c1 or not c2:
                continue
            pid = MATCH_BY_TEAMS.get((c1, c2))
            if not pid:
                continue
            et = score.get("et")  # resultado tras el alargue (si lo hubo)
            ft = score.get("ft")  # resultado en los 90 minutos
            ht = score.get("ht")  # entretiempo (fallback si el partido aún no terminó)
            # Prioridad: alargue > 90 minutos > entretiempo.
            # El campo "p" (penales) nunca se usa como resultado del partido.
            src = et if et is not None else (ft if ft is not None else ht)
            if not src or not isinstance(src, list) or len(src) < 2:
                continue
            g1, g2 = src[0], src[1]
            if g1 is not None and g2 is not None:
                resultados[pid] = {"l": str(g1), "v": str(g2)}
        return resultados if resultados else None
    except Exception as e:
        print(f"  ⚠️  Sin resultados automáticos: {e}")
        return None

# Bracket: qué partido de 16avos alimenta cada octavo (local, visita)
BRACKET_MAP = {
    "o1": ("r1", "r3"),   # Gan.r1 vs Gan.r3
    "o2": ("r4", "r5"),   # Gan.r4 vs Gan.r5
    "o3": ("r2", "r13"),  # Gan.r2 vs Gan.r13
    "o4": ("r7", "r8"),   # Gan.r7 vs Gan.r8
    "o5": ("r12","r11"),  # Gan.r12 vs Gan.r11
    "o6": ("r10","r9"),   # Gan.r10 vs Gan.r9
    "o7": ("r15","r14"),  # Gan.r15 vs Gan.r14
    "o8": ("r6", "r16"),  # Gan.r6 vs Gan.r16
}
QUARTERS_MAP = {
    "q1": ("o1","o2"), "q2": ("o3","o4"),
    "q3": ("o5","o6"), "q4": ("o7","o8"),
}
SEMIS_MAP = {"s1": ("q1","q2"), "s2": ("q3","q4")}

def get_winner(mid, resultados, penales, by_id):
    r = resultados.get(mid)
    if not r or r.get("l","") == "" or r.get("v","") == "":
        return None
    p = by_id.get(mid)
    if not p:
        return None
    gl, gv = int(r["l"]), int(r["v"])
    if gl > gv:
        return p["l"]
    if gv > gl:
        return p["v"]
    # Empate → penales
    lado = penales.get(mid)
    if lado == "l":
        return p["l"]
    if lado == "v":
        return p["v"]
    return None

def resolve_bracket(partidos, resultados, penales):
    by_id = {p["id"]: dict(p) for p in partidos}

    def apply(mapa):
        for mid, (lid, rid) in mapa.items():
            wl = get_winner(lid, resultados, penales, by_id)
            wr = get_winner(rid, resultados, penales, by_id)
            p = by_id[mid]
            if wl:
                p["l"] = wl
                p["lf"] = "⚽"
            if wr:
                p["v"] = wr
                p["vf"] = "⚽"

    apply(BRACKET_MAP)
    apply(QUARTERS_MAP)
    apply(SEMIS_MAP)

    # Final
    ws1 = get_winner("s1", resultados, penales, by_id)
    ws2 = get_winner("s2", resultados, penales, by_id)
    if ws1: by_id["f1"]["l"] = ws1; by_id["f1"]["lf"] = "🏆"
    if ws2: by_id["f1"]["v"] = ws2; by_id["f1"]["vf"] = "🏆"

    # Tercer puesto = perdedores de semis
    for semi, dest in [("s1","l"),("s2","v")]:
        w = get_winner(semi, resultados, penales, by_id)
        p = by_id[semi]
        if w:
            loser = p["v"] if w == p["l"] else p["l"]
            if dest == "l": by_id["t1"]["l"] = loser
            else:           by_id["t1"]["v"] = loser

    return list(by_id.values())

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault("penales", {})  # quien avanza cuando hay empate en eliminacion
                return data
        except:
            pass
    data = {"pronos": {}, "resultados": {}, "penales": {}}
    for u in USERS:
        data["pronos"][u] = {}
    return data

def save_data(data):
    """Guarda de forma segura — evita PermissionError en Windows."""
    tmp_path = DATA_FILE + ".tmp"
    try:
        # Escribir en archivo temporal primero
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # Si el destino existe y está bloqueado, intentar desbloquear
        if os.path.exists(DATA_FILE):
            try:
                import stat
                os.chmod(DATA_FILE, stat.S_IWRITE | stat.S_IREAD)
            except:
                pass
        os.replace(tmp_path, DATA_FILE)
    except Exception as e:
        print(f"  ❌ Error al guardar datos: {e}")
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass
        raise

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/data":
            data = load_data()
            resueltos = resolve_bracket(PARTIDOS, data.get("resultados",{}), data.get("penales",{}))
            data["partidos_resueltos"] = resueltos
            self.send_json(200, data)
        elif path == "/api/resultados-auto":
            data = load_data()
            live = fetch_live_results()
            if live:
                for k, v in live.items():
                    data["resultados"][k] = v
                save_data(data)
                nuevos = len(live)
                self.send_json(200, {"ok": True, "resultados": data["resultados"], "nuevos": nuevos})
            else:
                self.send_json(200, {"ok": True, "resultados": data["resultados"], "nuevos": 0})
        else:
            partidos_json = json.dumps(PARTIDOS, ensure_ascii=False)
            users_json = json.dumps(USERS, ensure_ascii=False)
            page = HTML.replace("__PARTIDOS__", partidos_json).replace("__USERS__", users_json)
            self.send_html(page)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        data = load_data()
        if path == "/api/pronos":
            user = body.get("user")
            if user in USERS:
                data["pronos"][user] = body.get("pronos", {})
                save_data(data)
                self.send_json(200, {"ok": True})
            else:
                self.send_json(400, {"error": "Usuario invalido"})
        elif path == "/api/resultados":
            data["resultados"] = body.get("resultados", {})
            save_data(data)
            self.send_json(200, {"ok": True})
        elif path == "/api/penales":
            # body: {rid: "r3", lado: "l"|"v"}  -> quien avanzo por penales
            rid = body.get("rid")
            lado = body.get("lado")
            if rid and lado in ("l", "v"):
                data.setdefault("penales", {})
                data["penales"][rid] = lado
                save_data(data)
                self.send_json(200, {"ok": True})
            else:
                self.send_json(400, {"error": "Datos invalidos"})
        else:
            self.send_json(404, {"error": "No encontrado"})

def run(port=None):
    if port is None:
        port = int(os.environ.get("PORT", 8000))
    ip = get_local_ip()
    if os.path.exists(DATA_FILE):
        try:
            import stat
            os.chmod(DATA_FILE, stat.S_IWRITE | stat.S_IREAD)
        except:
            pass
    server = http.server.HTTPServer(("0.0.0.0", port), Handler)
    print("=" * 54)
    print("  ⚽  PRODE MUNDIAL 2026 — 104 partidos  ⚽")
    print("=" * 54)
    print(f"  ✅ Servidor en puerto {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("  👋 Detenido.")

if __name__ == "__main__":
    run()
