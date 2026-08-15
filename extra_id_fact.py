import streamlit as st
import pdfplumber
import pypdf
import re
import io
import pandas as pd
from pathlib import Path

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Extractor de Facturas",
    page_icon="⚡",
    layout="centered",
)

# ── Styles ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .main { background: #F7F9FC; }

  .hero {
    background: linear-gradient(135deg, #00B4A6 0%, #004B6B 100%);
    border-radius: 14px;
    padding: 28px 32px 22px;
    margin-bottom: 28px;
    color: white;
  }
  .hero h1 { font-size: 1.7rem; font-weight: 700; margin: 0 0 4px; }
  .hero p  { font-size: 0.93rem; opacity: 0.85; margin: 0; }

  .result-card {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .badge-ok  { background:#D1FAE5; color:#065F46; border-radius:6px; padding:3px 10px; font-size:0.8rem; font-weight:600; }
  .badge-err { background:#FEE2E2; color:#991B1B; border-radius:6px; padding:3px 10px; font-size:0.8rem; font-weight:600; }
  .filename  { font-weight:600; color:#1E293B; font-size:0.95rem; }
  .factura   { color:#00B4A6; font-weight:700; font-size:1.05rem; }

  .stat-box {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 18px;
    text-align: center;
  }
  .stat-num  { font-size: 2rem; font-weight: 700; color: #004B6B; }
  .stat-lbl  { font-size: 0.82rem; color: #64748B; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>⚡ Extractor de Facturas</h1>
  <p>Sube uno o varios PDFs de facturas de servicios públicos y extrae el número de Factura electrónica de venta automáticamente.</p>
</div>
""", unsafe_allow_html=True)

# ── Core extraction logic ──────────────────────────────────────────────────────
PATTERNS = [
    # "Factura electrónica de venta N°:" seguido del número
    r"Factura\s+electr[oó]nica\s+de\s+venta\s+N[°o\.º]?\s*:?\s*([A-Z0-9\-]+)",
    # Número suelto con prefijos comunes: FESP, FE, FV, etc.
    r"\bFE(?:SP)?\s*\d{4,6}\b",
    # Fallback: cualquier cosa después de "N°"
    r"N[°º]\s*:?\s*([A-Z]{2,}\s*\d{3,})",
]

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extrae todo el texto del PDF usando pdfplumber (fallback: pypdf)."""
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception:
        pass

    if not text.strip():
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        except Exception:
            pass

    return text


def find_factura_number(text: str) -> str | None:
    """Busca el número de factura electrónica en el texto extraído."""
    for pattern in PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Si hay grupo capturado, devolver ese; si no, el match completo
            result = match.group(1) if match.lastindex else match.group(0)
            return result.strip()
    return None


# ── Upload widget ──────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Selecciona los archivos PDF",
    type=["pdf"],
    accept_multiple_files=True,
    help="Puedes subir varios PDFs a la vez.",
)

if uploaded:
    st.markdown("---")
    results = []

    with st.spinner("Procesando facturas…"):
        for f in uploaded:
            file_bytes = f.read()
            text = extract_text_from_pdf(file_bytes)
            numero = find_factura_number(text)
            results.append({
                "Archivo": f.name,
                "Factura electrónica N°": numero or "—",
                "_ok": numero is not None,
                "_text": text,
            })

    # ── Stats ──────────────────────────────────────────────────────────────────
    total = len(results)
    found = sum(1 for r in results if r["_ok"])
    not_found = total - found

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="stat-box"><div class="stat-num">{total}</div><div class="stat-lbl">PDFs procesados</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#065F46">{found}</div><div class="stat-lbl">Facturas encontradas</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#991B1B">{not_found}</div><div class="stat-lbl">Sin resultado</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Cards ──────────────────────────────────────────────────────────────────
    st.subheader("Resultados por archivo")
    for r in results:
        badge = '<span class="badge-ok">✓ Encontrado</span>' if r["_ok"] else '<span class="badge-err">✗ No encontrado</span>'
        numero_html = f'<span class="factura">{r["Factura electrónica N°"]}</span>' if r["_ok"] else '<span style="color:#94A3B8">No detectado</span>'
        st.markdown(f"""
        <div class="result-card">
          <div style="flex:1">
            <div class="filename">📄 {r["Archivo"]}</div>
            <div style="margin-top:4px;font-size:0.9rem;color:#475569">Factura N°: {numero_html}</div>
          </div>
          {badge}
        </div>
        """, unsafe_allow_html=True)

        # Expander de texto crudo (debug)
        if not r["_ok"] and r["_text"]:
            with st.expander(f"🔍 Ver texto extraído de {r['Archivo']}"):
                st.text(r["_text"][:3000] + ("…" if len(r["_text"]) > 3000 else ""))

    # ── Export CSV ─────────────────────────────────────────────────────────────
    st.markdown("---")
    df = pd.DataFrame([{
        "Archivo": r["Archivo"],
        "Factura electrónica N°": r["Factura electrónica N°"],
    } for r in results])

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="⬇ Descargar resultados en CSV",
        data=csv,
        file_name="facturas_extraidas.csv",
        mime="text/csv",
        use_container_width=True,
    )

else:
    st.info("👆 Sube tus PDFs arriba para comenzar.")
