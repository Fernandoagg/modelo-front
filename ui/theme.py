"""Sistema visual CaféSmart AI replicado de los mockups de alta fidelidad de Figma (IA-CafeSmart).

Contiene:
- `inject_theme()`: hoja de estilos global (tokens, tipografía, tarjetas, badges, tablas) y los
  overrides de los widgets nativos de Streamlit (sidebar, radio de navegación, selects, botones).
- Helpers de render (`html`, `icon`, `img_src`) usados por el shell y las páginas.

Los contenedores con `key="card_..."` se pintan como tarjeta blanca y los `key="surface_..."`
como superficie beige, lo que permite agrupar widgets nativos con el mismo look que el HTML.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"

# Tokens extraídos del Figma
C = {
    "bg": "#FAF9F5",
    "card": "#FFFFFF",
    "surface": "#F5F4ED",
    "surface_2": "#EFEEE7",
    "border": "#E9E7E0",
    "espresso_950": "#22140D",
    "espresso_900": "#2B1D16",
    "espresso_800": "#382820",
    "brown": "#7B5641",
    "terracotta": "#C77C55",
    "peach": "#FFDBCA",
    "peach_soft": "#FCEEE6",
    "sage": "#72856B",
    "sage_soft": "#E2EBDC",
    "text": "#1B1C18",
    "text_2": "#4F4540",
    "muted": "#81756F",
    "red": "#BA1A1A",
    "red_soft": "#FBE9E6",
    "amber": "#A3661C",
}


def html(raw: str) -> None:
    """Inserta HTML con `st.html` (sin parser Markdown: la sangría nunca se imprime como código)."""
    st.html("\n".join(line.strip() for line in raw.splitlines() if line.strip()))


def icon(name: str, size: int = 18, color: str | None = None, extra: str = "") -> str:
    """Icono Material Symbols Outlined (mismo trazo lineal que los iconos del Figma)."""
    style = f"font-size:{size}px;" + (f"color:{color};" if color else "") + extra
    return f'<span class="ms" style="{style}">{name}</span>'


@lru_cache(maxsize=32)
def img_src(filename: str) -> str:
    """Devuelve un data-URI base64 para una imagen de `assets/` (st.html no sirve archivos locales)."""
    path = ASSETS_DIR / filename
    if not path.exists():
        return ""
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def badge(text: str, variant: str = "neutral", dot: bool = False) -> str:
    dot_html = '<span class="b-dot"></span>' if dot else ""
    return f'<span class="badge b-{variant}">{dot_html}{text}</span>'


def page_header(
    title: str,
    subtitle: str = "",
    eyebrow: str = "",
    right: str = "",
    title_badge: str = "",
    divider: bool = True,
) -> None:
    """Encabezado editorial de cada vista (eyebrow + H1 + subtítulo + bloque derecho)."""
    html(
        f"""
        <div class="page-head{' with-divider' if divider else ''}">
            <div class="page-head-left">
                {f'<div class="eyebrow-row">{eyebrow}</div>' if eyebrow else ''}
                <div class="title-row"><h1 class="h1">{title}</h1>{title_badge}</div>
                {f'<p class="subtitle">{subtitle}</p>' if subtitle else ''}
            </div>
            {f'<div class="page-head-right">{right}</div>' if right else ''}
        </div>
        """
    )


def inject_theme() -> None:
    html(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,300..500,0..1,0&display=block');

:root{
  --bg:#FAF9F5;--card:#FFFFFF;--surface:#F5F4ED;--surface-2:#EFEEE7;--border:#E9E7E0;
  --e950:#22140D;--e900:#2B1D16;--e800:#382820;--brown:#7B5641;--terra:#C77C55;--peach:#FFDBCA;--peach-soft:#FCEEE6;
  --sage:#72856B;--sage-soft:#E2EBDC;--text:#1B1C18;--text-2:#4F4540;--muted:#81756F;--red:#BA1A1A;--red-soft:#FBE9E6;--amber:#A3661C;
  --mono:'JetBrains Mono',ui-monospace,monospace;--sans:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;
  --shadow:0 1px 2px rgba(34,20,13,0.05);
}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--bg)!important;}
html,body,.stMarkdown,p,label,input,button,textarea,select,li,td,th,h1,h2,h3,div{font-family:var(--sans);}
[data-testid="stIconMaterial"],span[data-testid="stIconMaterial"]{font-family:'Material Symbols Rounded'!important;}
.ms{font-family:'Material Symbols Outlined'!important;font-weight:400;font-style:normal;line-height:1;letter-spacing:normal;
    text-transform:none;display:inline-block;white-space:nowrap;-webkit-font-smoothing:antialiased;vertical-align:middle;
    font-variation-settings:'FILL' 0,'wght' 350,'GRAD' 0,'opsz' 24;}
.mono{font-family:var(--mono)!important;}

/* ---------- Chrome de Streamlit ---------- */
[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"] .stDeployButton{display:none!important;}
/* El stHeader nativo es fijo y transparente: queda ENCIMA de nuestro header y le robaba los clics.
   Se deja pasar el puntero, salvo en sus botones (p. ej. reabrir la barra lateral colapsada). */
header[data-testid="stHeader"]{background:transparent!important;pointer-events:none!important;}
header[data-testid="stHeader"] button,header[data-testid="stHeader"] a{pointer-events:auto!important;}
[data-testid="stMainBlockContainer"]{padding:12px 34px 60px 34px!important;max-width:1440px;}
[data-testid="stVerticalBlock"]{gap:14px;}
.stHtml{margin:0!important;}

/* ---------- Sidebar (Aside) ---------- */
[data-testid="stSidebar"]{background:#FFFFFF!important;border-right:1px solid var(--border)!important;min-width:300px!important;max-width:300px!important;}
[data-testid="stSidebar"] > div:first-child{padding-top:0!important;}
[data-testid="stSidebarContent"]{display:flex;flex-direction:column;}
[data-testid="stSidebarUserContent"]{padding:18px 16px 18px 16px!important;display:flex;flex-direction:column;min-height:100vh;}
[data-testid="stSidebarUserContent"] > div{flex:1;display:flex;flex-direction:column;}
[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"]{gap:10px;}
[data-testid="stSidebarHeader"]{padding:8px 8px 0 8px!important;height:auto!important;}
.side-brand{display:flex;align-items:center;gap:12px;padding:6px 6px 6px 6px;}
.side-logo{width:40px;height:40px;border-radius:8px;background:var(--e800);display:flex;align-items:center;justify-content:center;color:#EDD4C7;}
.side-title{font-size:17px;font-weight:600;color:var(--e950);letter-spacing:-0.02em;line-height:20px;}
.side-sub{font-size:10.5px;font-weight:600;color:var(--muted);letter-spacing:.09em;text-transform:uppercase;line-height:14px;}
.side-spacer{flex:1;}
.side-dataset{background:var(--surface);border-radius:6px;padding:9px 12px;}
.side-dataset .lbl{font-size:10.5px;font-weight:600;color:var(--muted);letter-spacing:.08em;}
.side-dataset .val{font-family:var(--mono);font-size:12.5px;color:var(--text);line-height:18px;}
.side-user{display:flex;align-items:center;gap:10px;padding:6px 4px 0 4px;}
.side-user img{width:34px;height:34px;border-radius:50%;object-fit:cover;}
.side-user .nm{font-size:13px;font-weight:600;color:var(--text);line-height:16px;}
.side-user .rl{font-size:10px;font-weight:600;color:var(--muted);letter-spacing:.08em;line-height:12px;}
.side-user .inf{margin-left:auto;color:var(--muted);}

/* selector "Sucursal activa" */
.st-key-w_store_side [data-baseweb="select"] > div{background:var(--surface)!important;border:none!important;border-radius:6px!important;min-height:34px!important;}
.st-key-w_store_side [data-baseweb="select"] div[value],.st-key-w_store_side [data-baseweb="select"] span{font-size:13px!important;color:var(--text)!important;}

/* navegación (radio) como lista del Aside */
.st-key-nav_radio [role="radiogroup"]{gap:2px!important;width:100%;}
.st-key-nav_radio [role="radiogroup"] > div{width:100%;}
.st-key-nav_radio [data-testid="stRadioOption"]{width:100%;margin:0!important;padding:10px 12px!important;border-radius:6px;cursor:pointer;transition:background .12s;}
.st-key-nav_radio [data-testid="stRadioOption"]:hover{background:var(--surface);}
.st-key-nav_radio [data-testid="stRadioOption"] > div > div:first-child{display:none!important;}
.st-key-nav_radio [data-testid="stRadioOption"] p{font-size:14px!important;color:var(--text-2)!important;font-weight:500!important;display:flex;align-items:center;gap:12px;line-height:19px;margin:0;}
.st-key-nav_radio [data-testid="stRadioOption"] p span[role="img"]{font-size:20px!important;color:var(--text-2)!important;}
.st-key-nav_radio [data-testid="stRadioOption"]:has(input:checked){background:var(--e800)!important;}
.st-key-nav_radio [data-testid="stRadioOption"]:has(input:checked) p,.st-key-nav_radio [data-testid="stRadioOption"]:has(input:checked) p span{color:#E7CFC1!important;font-weight:600!important;}

/* ---------- Header (barra fija superior) ---------- */
.st-key-app_header{background:#FFFFFF;border:1px solid var(--border);border-radius:8px;padding:10px 14px!important;box-shadow:var(--shadow);margin-bottom:8px;}
.st-key-app_header [data-testid="stHorizontalBlock"]{align-items:center!important;gap:12px!important;}
.crumb{display:flex;align-items:center;gap:10px;white-space:nowrap;}
.crumb .a{font-size:11px;font-weight:600;letter-spacing:.07em;color:var(--muted);}
.crumb .s{color:var(--muted);}
.crumb .b{font-size:13px;font-weight:600;color:var(--text);line-height:16px;white-space:nowrap;}
.hpill{display:flex;align-items:center;gap:8px;background:var(--surface);border-radius:6px;padding:7px 12px;min-height:38px;}
.hpill .t{font-size:13px;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.hpill.mono .t{font-family:var(--mono);font-size:12.5px;line-height:16px;}
.hpill.clima .t{white-space:normal;font-size:10.5px;font-weight:600;letter-spacing:.08em;color:var(--muted);text-transform:uppercase;line-height:13px;}
.hpill.clima.ok .t{color:var(--brown);}
.st-key-w_store_head [data-baseweb="select"] > div{background:var(--surface)!important;border:none!important;border-radius:6px!important;min-height:38px!important;}
.st-key-w_store_head [data-baseweb="select"] div{font-size:13.5px!important;}

/* ---------- Botones ---------- */
.stButton button,.stDownloadButton button,[data-testid="stPopover"] button,.stFormSubmitButton button{
  border-radius:6px!important;font-weight:500!important;font-size:13px!important;min-height:38px;box-shadow:none!important;}
.stButton button[kind="primary"],.stDownloadButton button[kind="primary"],[data-testid="stPopover"] button[kind="primary"],.stFormSubmitButton button[kind="primary"]{
  background:var(--e800)!important;border:1px solid var(--e800)!important;color:#FFFFFF!important;}
.stButton button[kind="primary"]:hover,.stDownloadButton button[kind="primary"]:hover,.stFormSubmitButton button[kind="primary"]:hover{background:var(--e950)!important;}
.stButton button[kind="secondary"],.stDownloadButton button[kind="secondary"],[data-testid="stPopover"] button[kind="secondary"],.stFormSubmitButton button[kind="secondary"]{
  background:var(--surface)!important;border:1px solid var(--surface)!important;color:var(--text)!important;}
.stButton button[kind="tertiary"]{color:var(--brown)!important;font-weight:600!important;}
.st-key-hdr_week button{background:var(--surface)!important;border:none!important;font-family:var(--mono)!important;}
.st-key-hdr_week button p{font-family:var(--mono)!important;font-size:12.5px!important;color:var(--text)!important;}

/* ---------- Inputs ---------- */
[data-testid="stWidgetLabel"] p{font-size:11px!important;font-weight:600!important;letter-spacing:.09em!important;text-transform:uppercase;color:var(--muted)!important;}
[data-baseweb="select"] > div,[data-baseweb="input"] > div,.stDateInput > div > div{background:var(--surface)!important;border-color:transparent!important;border-radius:6px!important;}
[data-testid="stSegmentedControl"] button{font-size:13px!important;}
[data-baseweb="select"] div{font-size:13.5px;}
[data-testid="stSegmentedControl"] button[aria-checked="true"],[data-testid="stSegmentedControl"] button[kind="segmented_controlActive"]{background:var(--e800)!important;color:#fff!important;border-color:var(--e800)!important;}
.stSlider [role="slider"]{background:var(--brown)!important;border-color:var(--brown)!important;}
.stCheckbox label span[role="checkbox"]{border-radius:3px!important;}

/* ---------- Contenedores con key ---------- */
[class*="st-key-card_"]{background:#FFFFFF;border:1px solid var(--border);border-radius:8px;padding:20px 22px!important;box-shadow:var(--shadow);}
[class*="st-key-surface_"]{background:var(--surface);border-radius:8px;padding:16px 18px!important;}
[class*="st-key-row_"]{border-bottom:1px solid var(--border);padding:12px 18px!important;background:#fff;}
[class*="st-key-row_"] [data-testid="stHorizontalBlock"]{align-items:center!important;}

.st-key-dark_roi{background:linear-gradient(160deg,#3E2D25 0%,#2B1D16 100%);border-radius:10px;padding:28px 30px!important;box-shadow:0 8px 24px rgba(34,20,13,.18);}
.st-key-dark_roi .stDownloadButton button{background:#7B5641!important;border-color:#7B5641!important;color:#fff!important;min-height:52px;}
.st-key-app_header .stDownloadButton button,.st-key-app_header .stButton button{min-height:42px;}
[class*="st-key-row_guia"]{border-radius:0;}
.st-key-surface_guia_head{border-radius:0;margin:0 -22px;padding:14px 40px!important;}

/* ---------- Tipografía y layout HTML ---------- */
.page-head{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;padding:18px 0 18px 0;flex-wrap:wrap;}
.page-head.with-divider{border-bottom:1px solid var(--border);margin-bottom:6px;}
.page-head-left{max-width:640px;flex:1 1 420px;}
.eyebrow-row{display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:11.5px;font-weight:600;letter-spacing:.09em;color:var(--muted);text-transform:uppercase;}
.title-row{display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.h1{font-size:34px!important;font-weight:700!important;color:var(--e950)!important;letter-spacing:-0.025em!important;margin:0!important;line-height:1.15!important;padding:0!important;}
.h1-xl{font-size:44px!important;}
.subtitle{font-size:16px;color:var(--text-2);margin:6px 0 0 0;line-height:24px;}
.h2{font-size:22px;font-weight:600;color:var(--e950);margin:0;letter-spacing:-0.015em;line-height:28px;}
.h3{font-size:17px;font-weight:600;color:var(--e950);margin:0;line-height:23px;}
.p{font-size:14px;color:var(--text-2);line-height:21px;margin:0;}
.small{font-size:12.5px;color:var(--muted);line-height:18px;}
.eyebrow{font-size:11.5px;font-weight:600;letter-spacing:.09em;color:var(--muted);text-transform:uppercase;line-height:16px;}
.eyebrow.brown{color:var(--brown);} .eyebrow.terra{color:var(--terra);} .eyebrow.red{color:var(--red);}
.num-chip{background:var(--e800);color:#fff;font-family:var(--mono);font-size:11px;padding:3px 6px;border-radius:3px;}

.card{background:#FFFFFF;border:1px solid var(--border);border-radius:8px;padding:20px 22px;box-shadow:var(--shadow);}
.card.tight{padding:16px 18px;}
.card.dark{background:linear-gradient(160deg,#3A2A22 0%,#2B1D16 100%);border-color:#2B1D16;color:#F2E6DF;}
.surface{background:var(--surface);border-radius:6px;padding:12px 14px;}
.hr{height:1px;background:var(--border);margin:12px 0;}
.row{display:flex;align-items:center;gap:10px;}
.between{display:flex;justify-content:space-between;align-items:center;gap:10px;}
.grid-2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;}
.grid-3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;}
.grid-4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;}
.grid-5{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;}

.badge{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:500;padding:4px 10px;border-radius:999px;line-height:16px;white-space:nowrap;}
.badge.sq{border-radius:4px;}
.b-dot{width:6px;height:6px;border-radius:50%;background:currentColor;display:inline-block;}
.b-peach{background:var(--peach-soft);color:#B2603A;border:1px solid #F3D3C1;}
.b-peach-solid{background:var(--peach);color:#7A3B1C;}
.b-sage{background:var(--sage-soft);color:#4E6847;}
.b-neutral{background:var(--surface-2);color:var(--text-2);}
.b-red{background:var(--red-soft);color:var(--red);}
.b-amber{background:#FBF0E2;color:var(--amber);}
.b-dark{background:var(--e800);color:#fff;}
.b-caps{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;}

/* KPI cards */
.kpi{background:#FFFFFF;border:1px solid var(--border);border-radius:8px;padding:18px 20px;box-shadow:var(--shadow);display:flex;flex-direction:column;justify-content:space-between;height:100%;min-height:170px;}
.kpi-top{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;}
.kpi-label{font-size:11.5px;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);line-height:16px;}
.kpi-value{font-family:var(--mono);font-size:36px;font-weight:500;color:var(--e950);letter-spacing:-0.02em;line-height:44px;margin-top:6px;}
.kpi-value.sm{font-size:22px;line-height:30px;}
.kpi-value.sans{font-family:var(--sans);font-weight:600;font-size:24px;line-height:30px;}
.kpi-unit{font-family:var(--sans);font-size:14px;color:var(--muted);margin-left:8px;font-weight:400;letter-spacing:0;}
.kpi-foot{border-top:1px solid var(--border);margin-top:12px;padding-top:10px;font-size:13.5px;color:var(--text-2);line-height:19px;}
.kpi-foot.nob{border-top:none;padding-top:4px;}
.bar{height:5px;background:var(--surface-2);border-radius:99px;overflow:hidden;margin-top:12px;}
.bar > div{height:100%;border-radius:99px;}

/* tablas */
.tbl-wrap{background:#FFFFFF;border:1px solid var(--border);border-radius:8px;overflow:hidden;box-shadow:var(--shadow);}
.tbl{width:100%;border-collapse:collapse;}
.tbl thead th{background:var(--surface);font-size:11.5px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);text-align:left;padding:16px 18px;}
.tbl thead th.num{font-family:var(--mono);}
.tbl td{padding:16px 18px;border-top:1px solid var(--border);font-size:14px;color:var(--text);vertical-align:middle;}
.tbl td.num,.tbl th.r{text-align:right;}
.tbl td.num{font-family:var(--mono);}
.tbl tfoot td{background:var(--surface);font-weight:600;}
.tbl-foot{display:flex;justify-content:space-between;align-items:center;padding:14px 22px;background:var(--surface);border-top:1px solid var(--border);font-size:13px;color:var(--muted);}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;}
.tag{display:inline-block;background:var(--surface);border-radius:4px;padding:4px 10px;font-size:13px;color:var(--text);}
.tag.mono{font-family:var(--mono);font-size:12.5px;}

/* foto */
.photo{position:relative;border-radius:8px;overflow:hidden;min-height:200px;background-size:cover;background-position:center;}
.photo::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 35%,rgba(34,20,13,.82) 100%);}
.photo .cap{position:absolute;left:18px;right:18px;bottom:16px;z-index:2;color:#fff;}
.photo .cap .e{font-size:11.5px;font-weight:600;letter-spacing:.1em;opacity:.85;}
.photo .cap .t{font-size:19px;font-weight:600;line-height:24px;}
.img-card{width:100%;height:200px;object-fit:cover;border-radius:6px;display:block;}

/* listas con check */
.checks{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px;}
.checks li{display:flex;gap:8px;font-size:13.5px;color:var(--text-2);line-height:19px;}
.checks li .ms{color:var(--terra);font-size:18px;}

@media (max-width: 1350px){ .crumb .a,.crumb .s{display:none;} }
.crumb{overflow:hidden;}
@media (max-width: 900px){
  .grid-3,.grid-4,.grid-5{grid-template-columns:repeat(2,minmax(0,1fr));}
  .h1{font-size:28px!important;}
}
</style>
"""
    )
