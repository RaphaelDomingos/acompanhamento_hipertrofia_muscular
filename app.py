import os
from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st

SENHA = "treino0714"  # troque aqui

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("Acesso restrito")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        st.session_state.auth = (senha == SENHA)
        if not st.session_state.auth:
            st.error("Senha incorreta")
    st.stop()

ARQ = "dados_treino.xlsx"

# -----------------------------
# Helpers
# -----------------------------
def readiness(sono_h, sono_q, estresse, energia, doms, dor):
    score = (sono_h*5 + sono_q*10 + (6-estresse)*8 + energia*10 + (10-doms)*4 + (10-dor)*4)
    return int(round(score))

def week_key(d: date):
    # Retorna "YYYY-Www" (semana ISO)
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"

def load_sheet(sheet_name: str, columns: list):
    if os.path.exists(ARQ):
        try:
            df = pd.read_excel(ARQ, sheet_name=sheet_name)
            # garante colunas mínimas
            for c in columns:
                if c not in df.columns:
                    df[c] = None
            return df[columns]
        except Exception:
            pass
    return pd.DataFrame(columns=columns)

def save_sheets(dfs: dict):
    with pd.ExcelWriter(ARQ, engine="openpyxl", mode="w") as writer:
        for name, df in dfs.items():
            df.to_excel(writer, sheet_name=name, index=False)

# -----------------------------
# Setup
# -----------------------------
st.set_page_config(page_title="Acompanhamento Treino", layout="wide")
st.title("Acompanhamento Inteligente – MJ & Raphael")

tabs = st.tabs(["✅ Check-in", "🏋️ Treino", "📈 Resumo Semanal", "🧾 Relatório Semanal", "💪 Controle por Músculo", "🔥 HIIT (Raphael)"])

# -----------------------------
# DataFrames base
# -----------------------------
CHECKIN_COLS = [
    "Data","Semana","Aluno","Sono_h","Sono_q","Estresse","Energia","DOMS","Dor_articular",
    "RPE_sessao","Observacao","Readiness"
]
TREINO_COLS = [
    "Data","Semana","Aluno","Sessao","Exercicio","Grupo_muscular","Carga_kg","Reps","Sets","RPE_exercicio","Tecnica","Observacao","Volume_kg"
]
HIIT_COLS = ["Data","Semana","Aluno","Tipo","Minutos","Esforco_1_10","Observacao"]

df_checkin = load_sheet("Checkin", CHECKIN_COLS)
df_treino  = load_sheet("Treino", TREINO_COLS)
df_hiit    = load_sheet("HIIT", HIIT_COLS)

# -----------------------------
# TAB 1: CHECK-IN
# -----------------------------
with tabs[0]:
    st.subheader("Check-in diário (1 minuto)")

    colA, colB = st.columns(2)
    with colA:
        aluno = st.selectbox("Aluno", ["MJ", "Raphael"], key="ci_aluno")
        data_ci = st.date_input("Data", value=date.today(), key="ci_data")
    with colB:
        rpe_sessao = st.slider("RPE da sessão (1–10) – se treinou", 1, 10, 8, key="ci_rpe")

    c1, c2, c3 = st.columns(3)
    with c1:
        sono_h = st.number_input("Sono (horas)", min_value=0.0, max_value=12.0, value=8.0, step=0.5, key="ci_sonoh")
        sono_q = st.slider("Qualidade do sono (1–5)", 1, 5, 4, key="ci_sonoq")
    with c2:
        estresse = st.slider("Estresse (1–5)", 1, 5, 3, key="ci_estresse")
        energia = st.slider("Energia (1–5)", 1, 5, 4, key="ci_energia")
    with c3:
        doms = st.slider("DOMS (0–10)", 0, 10, 1, key="ci_doms")
        dor = st.slider("Dor articular (0–10)", 0, 10, 0, key="ci_dor")

    obs = st.text_area("Observação rápida", value="", key="ci_obs")
    score = readiness(sono_h, sono_q, estresse, energia, doms, dor)
    st.metric("Readiness Score", score)

    if st.button("Salvar check-in", key="ci_save"):
        linha = {
            "Data": pd.to_datetime(data_ci),
            "Semana": week_key(data_ci),
            "Aluno": aluno,
            "Sono_h": sono_h,
            "Sono_q": sono_q,
            "Estresse": estresse,
            "Energia": energia,
            "DOMS": doms,
            "Dor_articular": dor,
            "RPE_sessao": rpe_sessao,
            "Observacao": obs,
            "Readiness": score,
        }
        df_checkin = pd.concat([df_checkin, pd.DataFrame([linha])], ignore_index=True)
        save_sheets({"Checkin": df_checkin, "Treino": df_treino, "HIIT": df_hiit})
        st.success(f"Check-in salvo em {ARQ} ✅")

    st.divider()
    st.caption("Últimos check-ins")
    st.dataframe(df_checkin.tail(20), use_container_width=True)

# -----------------------------
# TAB 2: TREINO (Lote)
# -----------------------------
with tabs[1]:
    st.subheader("Registro de treino (em lote)")

    # Buffer para armazenar exercícios antes de salvar
    if "workout_buffer" not in st.session_state:
        st.session_state.workout_buffer = []

    # Cabeçalho do treino do dia
    colA, colB, colC, colD = st.columns(4)
    with colA:
        aluno_t = st.selectbox("Aluno", ["MJ", "Raphael"], key="tr_aluno")
    with colB:
        data_t = st.date_input("Data do treino", value=date.today(), key="tr_data")
    with colC:
        sessao = st.selectbox("Sessão", ["D1", "D2", "D3", "D4"], key="tr_sessao")
    with colD:
        tecnica_padrao = st.selectbox(
            "Técnica padrão (opcional)",
            ["N/A","Drop set","Rest-pause","Bi-set","Pré-exaustão"],
            key="tr_tecnica_padrao"
        )

    st.markdown("### Adicionar exercício ao treino do dia")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        exercicio = st.text_input("Exercício (ex.: Puxada alta Hammer)", key="tr_exercicio")
    with col2:
        grupo = st.selectbox(
            "Grupo muscular (principal)",
            ["Peito","Costas","Ombros","Bíceps","Tríceps","Quadríceps","Posterior","Glúteos","Panturrilha","Core","Cardio"],
            key="tr_grupo"
        )
    with col3:
        carga = st.number_input("Carga (kg)", min_value=0.0, max_value=500.0, value=20.0, step=1.0, key="tr_carga")
        reps = st.number_input("Reps", min_value=1, max_value=50, value=10, step=1, key="tr_reps")
    with col4:
        sets = st.number_input("Sets", min_value=1, max_value=20, value=3, step=1, key="tr_sets")
        rpe_ex = st.slider("RPE (1–10)", 1, 10, 8, key="tr_rpe_ex")

    tecnica = st.selectbox(
        "Técnica (opcional) para este exercício",
        ["(usar padrão)","N/A","Drop set","Rest-pause","Bi-set","Pré-exaustão"],
        key="tr_tecnica_ex"
    )
    obs_t = st.text_input("Observação (opcional)", key="tr_obs")

    # Calcula volume
    volume = float(carga) * int(reps) * int(sets)
    st.metric("Volume (kg)", int(volume))

    # Botões: adicionar ao buffer / limpar buffer
    col_btn1, col_btn2, col_btn3 = st.columns([1,1,2])
    with col_btn1:
        if st.button("➕ Adicionar à lista", key="tr_add_buffer"):
            if not exercicio.strip():
                st.error("Digite o nome do exercício.")
            else:
                tecnica_final = tecnica_padrao if tecnica == "(usar padrão)" else tecnica
                st.session_state.workout_buffer.append({
                    "Data": pd.to_datetime(data_t),
                    "Semana": week_key(data_t),
                    "Aluno": aluno_t,
                    "Sessao": sessao,
                    "Exercicio": exercicio.strip(),
                    "Grupo_muscular": grupo,
                    "Carga_kg": float(carga),
                    "Reps": int(reps),
                    "Sets": int(sets),
                    "RPE_exercicio": int(rpe_ex),
                    "Tecnica": tecnica_final,
                    "Observacao": obs_t,
                    "Volume_kg": float(volume),
                })
                st.success("Adicionado à lista do treino ✅")

    with col_btn2:
        if st.button("🧹 Limpar lista", key="tr_clear_buffer"):
            st.session_state.workout_buffer = []
            st.info("Lista do treino limpa.")

    st.divider()
    st.markdown("### Exercícios do treino do dia (prévia)")

    if len(st.session_state.workout_buffer) == 0:
        st.warning("Nenhum exercício na lista ainda. Adicione acima.")
    else:
        df_buffer = pd.DataFrame(st.session_state.workout_buffer)
        st.dataframe(df_buffer, use_container_width=True)

        # Remover item específico
        idx = st.number_input(
            "Remover exercício pelo índice (0, 1, 2...)", min_value=0,
            max_value=max(0, len(st.session_state.workout_buffer)-1),
            value=0, step=1, key="tr_remove_idx"
        )
        if st.button("🗑️ Remover índice", key="tr_remove_btn"):
            try:
                st.session_state.workout_buffer.pop(int(idx))
                st.success("Removido ✅")
            except Exception:
                st.error("Não consegui remover. Verifique o índice.")

        st.divider()

        # Salvar o treino do dia (lote)
        if st.button("💾 Salvar treino do dia (tudo)", key="tr_save_all"):
            df_new = pd.DataFrame(st.session_state.workout_buffer)
            df_treino = pd.concat([df_treino, df_new], ignore_index=True)
            save_sheets({"Checkin": df_checkin, "Treino": df_treino, "HIIT": df_hiit})
            st.session_state.workout_buffer = []
            st.success(f"Treino salvo em {ARQ} ✅")

    st.divider()
    st.caption("Últimos exercícios registrados (já salvos no arquivo)")

    # Mostrar últimos registros COM índice real
    ultimos = df_treino.tail(25).copy()
    ultimos = ultimos.reset_index()  # mantém índice original
    st.dataframe(ultimos, use_container_width=True)
    
    st.markdown("### 🗑️ Excluir exercício salvo")
    
    col_del1, col_del2 = st.columns(2)
    with col_del1:
        idx_del = st.number_input(
            "Índice do exercício a excluir",
            min_value=int(ultimos["index"].min()),
            max_value=int(ultimos["index"].max()),
            step=1
        )
    
    with col_del2:
        confirmar = st.checkbox("Confirmar exclusão")
    
    if st.button("❌ Excluir exercício"):
        if not confirmar:
            st.warning("Marque a confirmação para excluir.")
        else:
            try:
                df_treino = df_treino.drop(index=idx_del).reset_index(drop=True)
                save_sheets({"Checkin": df_checkin, "Treino": df_treino, "HIIT": df_hiit})
                st.success("Exercício excluído com sucesso ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")

# -----------------------------
# TAB 3: RESUMO SEMANAL
# -----------------------------
with tabs[2]:
    st.subheader("Resumo semanal automático")

    semanas = sorted(set(list(df_checkin["Semana"].dropna()) + list(df_treino["Semana"].dropna())))
    if not semanas:
        st.info("Ainda não há dados suficientes. Registre check-ins e treinos.")
    else:
        semana_sel = st.selectbox("Selecione a semana", semanas[::-1], key="rs_semana")

        def resumo_aluno(nome):
            ci = df_checkin[(df_checkin["Aluno"] == nome) & (df_checkin["Semana"] == semana_sel)]
            tr = df_treino[(df_treino["Aluno"] == nome) & (df_treino["Semana"] == semana_sel)]

            readiness_med = float(ci["Readiness"].mean()) if len(ci) else None
            rpe_med = float(ci["RPE_sessao"].mean()) if len(ci) else None
            volume_total = float(tr["Volume_kg"].sum()) if len(tr) else 0.0
            sets_total = int(tr["Sets"].sum()) if len(tr) else 0

            decisao = "MANTER"
            if readiness_med is not None:
                if readiness_med >= 75:
                    decisao = "PROGREDIR"
                elif readiness_med >= 60:
                    decisao = "MANTER"
                else:
                    decisao = "REDUZIR"

            return {
                "Aluno": nome,
                "Semana": semana_sel,
                "Readiness médio": None if readiness_med is None else round(readiness_med, 1),
                "RPE médio": None if rpe_med is None else round(rpe_med, 1),
                "Sets (total)": sets_total,
                "Volume total (kg)": int(volume_total),
                "Decisão": decisao
            }

        resumo = pd.DataFrame([resumo_aluno("MJ"), resumo_aluno("Raphael")])
        st.dataframe(resumo, use_container_width=True)

        st.caption("Dica: decisão é baseada principalmente no Readiness médio (recuperação).")

# -----------------------------
# TAB 4: RELATÓRIO SEMANAL (Markdown Prompt)
# -----------------------------
with tabs[3]:
    st.subheader("Relatório Semanal (copiar/colar para o Mestre GPT)")

    semanas = sorted(set(list(df_checkin["Semana"].dropna()) + list(df_treino["Semana"].dropna()) + list(df_hiit["Semana"].dropna())))
    if not semanas:
        st.info("Ainda não há dados suficientes.")
    else:
        semana_sel = st.selectbox("Selecione a semana", semanas[::-1], key="rel_semana")

        def build_student_report(nome):
            ci = df_checkin[(df_checkin["Aluno"] == nome) & (df_checkin["Semana"] == semana_sel)].copy()
            tr = df_treino[(df_treino["Aluno"] == nome) & (df_treino["Semana"] == semana_sel)].copy()
            hi = df_hiit[(df_hiit["Aluno"] == nome) & (df_hiit["Semana"] == semana_sel)].copy()

            readiness_med = ci["Readiness"].mean() if len(ci) else None
            rpe_med = ci["RPE_sessao"].mean() if len(ci) else None
            sono_med = ci["Sono_h"].mean() if len(ci) else None
            estresse_med = ci["Estresse"].mean() if len(ci) else None
            dor_med = ci["Dor_articular"].mean() if len(ci) else None

            volume_total = tr["Volume_kg"].sum() if len(tr) else 0
            sets_total = tr["Sets"].sum() if len(tr) else 0

            # Top músculos por sets
            if len(tr):
                by_m = tr.groupby("Grupo_muscular").agg(
                    sets=("Sets","sum"),
                    volume=("Volume_kg","sum")
                ).reset_index().sort_values("sets", ascending=False)
                top_m = by_m.head(6)
            else:
                top_m = pd.DataFrame(columns=["Grupo_muscular","sets","volume"])

            # HIIT
            hiit_count = len(hi)
            hiit_minutes = hi["Minutos"].sum() if len(hi) else 0

            # Alertas simples
            alerts = []
            if readiness_med is not None and readiness_med < 60:
                alerts.append("Readiness médio < 60 (recuperação baixa).")
            if dor_med is not None and dor_med >= 4:
                alerts.append("Dor articular média elevada (>=4).")
            if nome.lower().startswith("raphael") or nome == "Raphael":
                if hiit_count < 2:
                    alerts.append("HIIT < 2x na semana (metabólico pendente).")

            return {
                "nome": nome,
                "readiness_med": None if readiness_med is None else round(float(readiness_med), 1),
                "rpe_med": None if rpe_med is None else round(float(rpe_med), 1),
                "sono_med": None if sono_med is None else round(float(sono_med), 1),
                "estresse_med": None if estresse_med is None else round(float(estresse_med), 1),
                "dor_med": None if dor_med is None else round(float(dor_med), 1),
                "volume_total": int(round(float(volume_total), 0)),
                "sets_total": int(sets_total),
                "top_m": top_m,
                "hiit_count": int(hiit_count),
                "hiit_minutes": int(hiit_minutes),
                "alerts": alerts
            }

        # Nomes conforme seu app
        rep_mj = build_student_report("MJ")
        rep_rap = build_student_report("Raphael")

        def fmt_top_m(df):
            if df is None or df.empty:
                return "- (sem dados de treino registrados na semana)\n"
            lines = []
            for _, r in df.iterrows():
                lines.append(f"- {r['Grupo_muscular']}: **{int(r['sets'])} sets**, volume **{int(r['volume'])} kg**")
            return "\n".join(lines) + "\n"

        prompt_md = f"""# Relatório Semanal – Semana {semana_sel}

Você é meu consultor de treino (hipertrofia + performance + recuperação). Com base nos dados abaixo, gere:
1) Diagnóstico da semana (MJ e Raphael)
2) Ajustes no próximo microciclo (volume por músculo, progressão, técnicas)
3) Alertas e ações preventivas (dor, fadiga, sono, HIIT)
4) Objetivos práticos para a semana seguinte (3 bullets por aluno)

---

## MJ
- Readiness médio: **{rep_mj['readiness_med']}**
- RPE médio (sessão): **{rep_mj['rpe_med']}**
- Sono médio (h): **{rep_mj['sono_med']}**
- Estresse médio: **{rep_mj['estresse_med']}**
- Dor articular média: **{rep_mj['dor_med']}**
- Sets totais: **{rep_mj['sets_total']}**
- Volume total: **{rep_mj['volume_total']} kg**

**Top músculos (sets/volume):**
{fmt_top_m(rep_mj['top_m'])}
**Alertas:**
- {("Nenhum." if len(rep_mj['alerts'])==0 else " | ".join(rep_mj['alerts']))}

---

## Raphael
- Readiness médio: **{rep_rap['readiness_med']}**
- RPE médio (sessão): **{rep_rap['rpe_med']}**
- Sono médio (h): **{rep_rap['sono_med']}**
- Estresse médio: **{rep_rap['estresse_med']}**
- Dor articular média: **{rep_rap['dor_med']}**
- Sets totais: **{rep_rap['sets_total']}**
- Volume total: **{rep_rap['volume_total']} kg**
- HIIT na semana: **{rep_rap['hiit_count']}x** | **{rep_rap['hiit_minutes']} min**

**Top músculos (sets/volume):**
{fmt_top_m(rep_rap['top_m'])}
**Alertas:**
- {("Nenhum." if len(rep_rap['alerts'])==0 else " | ".join(rep_rap['alerts']))}
"""

        st.markdown("### Prompt (Markdown) pronto para copiar")
        st.code(prompt_md, language="markdown")

        st.download_button(
            "⬇️ Baixar relatório (.md)",
            data=prompt_md.encode("utf-8"),
            file_name=f"relatorio_{semana_sel}.md",
            mime="text/markdown"
        )

# -----------------------------
# TAB 5: CONTROLE POR MÚSCULO
# -----------------------------
with tabs[3]:
    st.subheader("Controle por músculo (sets e volume)")

    semanas = sorted(df_treino["Semana"].dropna().unique().tolist())
    if not semanas:
        st.info("Registre exercícios na aba Treino para habilitar este painel.")
    else:
        semana_m = st.selectbox("Semana", semanas[::-1], key="cm_semana")
        aluno_m = st.selectbox("Aluno", ["MJ", "Raphael"], key="cm_aluno")

        tr = df_treino[(df_treino["Aluno"] == aluno_m) & (df_treino["Semana"] == semana_m)].copy()
        if tr.empty:
            st.warning("Sem exercícios nessa semana para este aluno.")
        else:
            agg = tr.groupby("Grupo_muscular").agg(
                Sets_totais=("Sets","sum"),
                Volume_total_kg=("Volume_kg","sum")
            ).reset_index()

            def status_sets(x):
                if x < 10:
                    return "BAIXO"
                if x <= 18:
                    return "ADEQUADO"
                return "EXCESSIVO"

            agg["Status"] = agg["Sets_totais"].apply(status_sets)
            agg["Volume_total_kg"] = agg["Volume_total_kg"].round(0).astype(int)
            st.dataframe(agg.sort_values("Sets_totais", ascending=False), use_container_width=True)

# -----------------------------
# TAB 6: HIIT (Raphael)
# -----------------------------
with tabs[4]:
    st.subheader("HIIT / Cardio – foco Raphael")

    aluno_h = st.selectbox("Aluno", ["Raphael", "MJ"], index=0, key="hiit_aluno")
    data_h = st.date_input("Data", value=date.today(), key="hiit_data")
    tipo = st.selectbox("Tipo", ["HIIT Esteira","HIIT Bike","Caminhada","Corrida leve","Outro"], key="hiit_tipo")
    col1, col2, col3 = st.columns(3)
    with col1:
        minutos = st.number_input("Minutos", min_value=1, max_value=180, value=20, step=1, key="hiit_min")
    with col2:
        esforco = st.slider("Esforço (1–10)", 1, 10, 8, key="hiit_esf")
    with col3:
        obs_h = st.text_input("Observação", key="hiit_obs")

    if st.button("Salvar HIIT", key="hiit_save"):
        linha = {
            "Data": pd.to_datetime(data_h),
            "Semana": week_key(data_h),
            "Aluno": aluno_h,
            "Tipo": tipo,
            "Minutos": int(minutos),
            "Esforco_1_10": int(esforco),
            "Observacao": obs_h,
        }
        df_hiit = pd.concat([df_hiit, pd.DataFrame([linha])], ignore_index=True)
        save_sheets({"Checkin": df_checkin, "Treino": df_treino, "HIIT": df_hiit})
        st.success("HIIT salvo ✅")

    st.divider()
    st.caption("Últimos registros de HIIT")
    st.dataframe(df_hiit.tail(20), use_container_width=True)

st.caption(f"Arquivo de dados: {ARQ}")





