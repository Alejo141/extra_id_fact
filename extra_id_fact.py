import streamlit as st
import re
import io
import pandas as pd

st.set_page_config(page_title="Extractor de Facturas", page_icon="⚡", layout="centered")

st.markdown("""
<style>
  .hero {
    background: linear-gradient(135deg, #00B4A6 0%, #004B6B 100%);
    border-radius: 14px; padding: 28px 32px 22px; margin-bottom: 28px; color: white;
  }
  .hero h1 { font-size: 1.7rem; font-weight: 700; margin: 0 0 4px; }
  .hero p  { font-size: 0.93rem; opacity: 0.85; margin: 0; }
  .result-card {
    background: white; border: 1px solid #E2E8F0; border-radius: 10px;
    padding: 16px 20px; margin-bottom: 10px;
  }
  .badge-ok  { background:#D1FAE5; color:#065F46; border-radius:6px; padding:3px 10px; font-size:0.8rem; font-weight:600; }
  .badge-err { background:#FEE2E2; color:#991B1B; border-radius:6px; padding:3px 10px; font-size:0.8rem; font-weight:600; }
  .factura   { color:#00B4A6; font-weight:700; font-size:1.05rem; }
  .stat-box  { background:white; border:1px solid #E2E8F0; border-radius:10px; padding:18px; text-align:center; }
  .stat-num  { font-size:2rem; font-weight:700; color:#004B6B; }
  .stat-lbl  { font-size:0.82rem; color:#64748B; margin-top:2px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>⚡ Extractor de Facturas</h1>
  <p>Sube uno o varios PDFs y extrae el número de Factura electrónica de venta.</p>
</div>
""", unsafe_allow_html=True)

PATTERNS = [
    r"Factura\s+electr[oó]nica\s+de\s+venta\s+N[°o\.º]?\s*:?\s*([A-Z0-9\-]+)",
    r"\bFE(?:SP)?\s*\d{4,6}\b",
    r"N[°º]\s*:?\s*([A-Z]{2,}\s*\d{3,})",
]

def extract_text_pdf_raw(file_bytes: bytes) -> str:
    """Extrae texto de un PDF usando solo la librería estándar de Python."""
    try:
        raw = file_bytes.decode("latin-1", errors="ignore")
        # Extraer bloques de texto entre BT y ET (operadores PDF)
        chunks = re.findall(r'BT(.*?)ET', raw, re.DOTALL)
        texts = []
        for chunk in chunks:
            # Strings entre paréntesis: (texto)
            parts = re.findall(r'\(([^)]*)\)', chunk)
            texts.extend(parts)
        text = " ".join(texts)
        # Limpiar caracteres de control
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', text)
        return text
    except Exception:
        return ""

def find_factura_number(text: str):
    for pattern in PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result = match.group(1) if match.lastindex else match.group(0)
            return result.strip()
    return None

uploaded = st.file_uploader(
    "Selecciona los archivos PDF",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded:
    st.markdown("---")
    results = []

    with st.spinner("Procesando facturas…"):
        for f in uploaded:
            file_bytes = f.read()
            text = extract_text_pdf_raw(file_bytes)
            numero = find_factura_number(text)
            results.append({
                "Archivo": f.name,
                "Factura electrónica N°": numero or "—",
                "_ok": numero is not None,
                "_text": text,
            })

    total = len(results)
    found = sum(1 for r in results if r["_ok"])
    not_found = total - found

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="stat-box"><div class="stat-num">{total}</div><div class="stat-lbl">PDFs procesados</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#065F46">{found}</div><div class="stat-lbl">Encontradas</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#991B1B">{not_found}</div><div class="stat-lbl">Sin resultado</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Resultados por archivo")

    for r in results:
        badge = '<span class="badge-ok">✓ Encontrado</span>' if r["_ok"] else '<span class="badge-err">✗ No encontrado</span>'
        numero_html = f'<span class="factura">{r["Factura electrónica N°"]}</span>' if r["_ok"] else '<span style="color:#94A3B8">No detectado</span>'
        st.markdown(f"""
        <div class="result-card">
          <div style="margin-bottom:6px"><strong>📄 {r["Archivo"]}</strong> &nbsp; {badge}</div>
          <div style="font-size:0.9rem;color:#475569">Factura N°: {numero_html}</div>
        </div>
        """, unsafe_allow_html=True)

        if not r["_ok"] and r["_text"]:
            with st.expander(f"🔍 Texto extraído de {r['Archivo']} (debug)"):
                st.text(r["_text"][:3000])

    st.markdown("---")
    df = pd.DataFrame([{"Archivo": r["Archivo"], "Factura electrónica N°": r["Factura electrónica N°"]} for r in results])
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇ Descargar CSV", data=csv, file_name="facturas_extraidas.csv", mime="text/csv", use_container_width=True)

else:
    st.info("👆 Sube tus PDFs arriba para comenzar.")
