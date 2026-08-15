import streamlit as st
import re
import io
import base64
import json
import urllib.request
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
  <p>Sube uno o varios PDFs y extrae el número de Factura electrónica de venta usando IA.</p>
</div>
""", unsafe_allow_html=True)

# ── API Key ────────────────────────────────────────────────────────────────────
api_key = st.text_input("🔑 API Key de Anthropic", type="password",
                        help="Consíguela en console.anthropic.com")

if not api_key:
    st.info("Ingresa tu API Key de Anthropic para comenzar.")
    st.stop()

def extract_factura_with_claude(pdf_bytes: bytes, api_key: str) -> str:
    """Envía el PDF a Claude y pide que extraiga el número de factura."""
    b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    payload = {
        "model": "claude-opus-4-6",
        "max_tokens": 200,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": b64
                        }
                    },
                    {
                        "type": "text",
                        "text": (
                            "En este PDF hay una factura de servicios públicos. "
                            "Busca el campo 'Factura electrónica de venta N°' y extrae SOLO su valor "
                            "(ejemplo: FESP 26051). "
                            "Responde únicamente con el valor, sin texto adicional. "
                            "Si no lo encuentras, responde exactamente: NO_ENCONTRADO"
                        )
                    }
                ]
            }
        ]
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            text = result["content"][0]["text"].strip()
            return None if text == "NO_ENCONTRADO" else text
    except Exception as e:
        return f"ERROR: {e}"

# ── Upload ─────────────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Selecciona los archivos PDF",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded:
    st.markdown("---")
    results = []

    progress = st.progress(0, text="Procesando…")
    for i, f in enumerate(uploaded):
        progress.progress((i) / len(uploaded), text=f"Procesando {f.name}…")
        file_bytes = f.read()
        numero = extract_factura_with_claude(file_bytes, api_key)
        ok = numero is not None and not str(numero).startswith("ERROR")
        results.append({
            "Archivo": f.name,
            "Factura electrónica N°": numero or "—",
            "_ok": ok,
            "_error": numero if str(numero or "").startswith("ERROR") else None,
        })
    progress.progress(1.0, text="¡Listo!")

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
        numero_html = f'<span class="factura">{r["Factura electrónica N°"]}</span>' if r["_ok"] else '<span style="color:#94A3B8">{}</span>'.format(r["Factura electrónica N°"])
        st.markdown(f"""
        <div class="result-card">
          <div style="margin-bottom:6px"><strong>📄 {r["Archivo"]}</strong> &nbsp; {badge}</div>
          <div style="font-size:0.9rem;color:#475569">Factura N°: {numero_html}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    df = pd.DataFrame([{"Archivo": r["Archivo"], "Factura electrónica N°": r["Factura electrónica N°"]} for r in results])
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇ Descargar CSV", data=csv, file_name="facturas_extraidas.csv", mime="text/csv", use_container_width=True)

else:
    st.info("👆 Sube tus PDFs arriba para comenzar.")
