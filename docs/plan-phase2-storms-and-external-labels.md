# Phase 2 Plan — Robustez via tempestades magnéticas + rótulos externos

> **Status**: aprovado e em execução. Documento vivo — atualize ao implementar.
>
> **Antecedentes**: Phase 1 (MVP) entregou ingest, features, weak-labels (Pi 1997 / Cherniak 2014), XGBoost, snapshot v0, FastAPI, Next.js + mapa, fig02 e infraestrutura de testes/CI. PR-AUC validation = 0.9999, mas isso é circular (modelo aprende a heurística sobre as mesmas features). Falta validação independente e contexto físico.

## Contexto científico

Bolhas de plasma equatoriais (EPBs) não respondem monotonicamente a tempestades magnéticas. Dois mecanismos atuam:

1. **PPEF (Prompt Penetration Electric Field)** durante a fase principal — um campo elétrico de origem magnetosférica vaza para baixas latitudes. Pode reforçar (eastward em horário pré-reversão) ou suprimir (westward) o pré-reversão (PRE) que origina as bolhas.
2. **DDEF (Disturbance Dynamo)** na fase de recuperação — vento neutro alterado modula o PRE no dia seguinte e tipicamente **suprime** EPBs na noite pós-tempestade.

Resultado: a relação tempestade ↔ EPB é dependente da **hora local da fase principal**. Esse é o fenômeno físico que vamos mostrar quantitativamente no paper.

## O que muda na Phase 2

| Frente | Phase 1 | Phase 2 |
|--------|---------|---------|
| Rótulos | só heurística (weak-v1) | weak-v1 + lista de casos publicados (literature-v1) com confiança graduada |
| Contexto | nenhum | Kp, ap, Dst, F10.7, IMF Bz integrados no nível de janela |
| Modelo | XGBoost sobre 18 features | XGBoost sobre 24+ features (com space weather) e gate de confiança |
| Web | home, map, dataset, methods | + `/storms` com timeline Kp/Dst + comparação storm-vs-quiet |
| Paper | fig02 evento exemplo | + fig10 storm-vs-quiet PR + fig11 superposed epoch |
| Tests | 47 Python + 6 Playwright | + suíte para space weather, storm classifier, external labels, /storms |

## Fontes de dados

### Space weather (todas públicas, sem auth)

| Índice | Cadência | Fonte | URL |
|--------|----------|-------|-----|
| Kp / ap / SN / F10.7 | 3h / diária | GFZ Potsdam | `https://kp.gfz-potsdam.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt` |
| Dst (definitivo) | 1h | WDC Kyoto | `https://wdc.kugi.kyoto-u.ac.jp/dst_final/<YYYYMM>/dst<YYMM>.for.request` |
| Dst (provisional) | 1h | WDC Kyoto | `https://wdc.kugi.kyoto-u.ac.jp/dst_provisional/<YYYYMM>/dst<YYMM>.for.request` |
| OMNIWeb HRO 1-min (IMF Bz, Vsw, Np, AE) | 1m | NASA SPDF | `https://spdf.gsfc.nasa.gov/pub/data/omni/high_res_omni/monthly_1min/` |

**Cache**: tudo persiste em `data/space_weather/<index>.parquet` particionado por ano. Refetch programático com TTL de 24h.

### Rótulos externos

**Plano A — começar com lista de casos publicados** (implementado já): YAML curado em `src/epb_detector/external/case_studies.yaml` com eventos (data, estação, fase de tempestade, DOI). Pequeno (~50 eventos) mas alta qualidade.

**Plano B — EMBRACE/INPE S4** (próxima iteração): requer registro em https://www2.inpe.br/climaespacial/portal/. Stub criado em `external/embrace.py` com NotImplementedError + nota de acesso. Quando a chave for obtida, rótulo automático fica disponível.

**Plano C — GOLD imagery (NASA, 2018+)** (futuro): imagens 135.6 nm do disco terrestre mostram plumas. Acessível via SPDF sem auth. Útil como ground-truth visual mas exige CV. Stub apenas.

## Classificação de tempestades

```
Quiet         : Dst > -30 nT
Moderate      : -50 < Dst ≤ -30 nT
Intense       : -100 < Dst ≤ -50 nT
Severe        : -250 < Dst ≤ -100 nT
Super         : Dst ≤ -250 nT
```

Fases (definidas pela derivada de Dst):
- **Initial phase**: SSC step (raro — geralmente ignorado).
- **Main phase**: queda monotônica até Dst min.
- **Recovery phase**: recuperação até Dst > -30 nT.

Cada janela de feature herda:
- `kp_3h`, `ap_3h`, `dst_1h`, `f107_d`, `imf_bz_avg_1h`, `vsw_avg_1h`
- `storm_class` ∈ {quiet, moderate, intense, severe, super}
- `storm_phase` ∈ {none, main, recovery}
- `hours_from_dst_min` (NaN se não em tempestade ±48h)

## Estratégia de rotulagem v2

```
final_label = max(weak_v1, literature_v1)
confidence  = 1.0  se ambos concordam positivos
            = 0.7  se literature_v1 = positivo (case publicado)
            = 0.5  se só weak_v1 = positivo
            = 0.0  se ambos negativos
```

Treino usa `confidence ≥ 0.5` (mantém recall). Validação usa `confidence ≥ 0.7` (alta qualidade) → métrica honesta de generalização.

## Robustez do modelo

1. **Cross-station holdout** (`splits/holdout.py`): treina em BOAV+SALU, valida em POAL. Mede generalização geográfica.
2. **Storm-vs-quiet PR-AUC** (`models/metrics.py`): métrica reportada separadamente para storm e quiet. Esperado: queda em storm.
3. **Calibração isotônica em fold dedicado** (já existe). Adicionar reliability diagram (fig05).
4. **Feature importance auditada** (`models/explain.py`): SHAP por subgrupo (storm vs quiet).
5. **Floor de PR-AUC no holdout literature-v1**: ≥ 0.65 (critério honesto, antes era circular).

## Web — /storms

**Página `/storms`**:
- **Hero**: contagem de tempestades (Kp ≥ 5) no período + Dst mais intenso.
- **Timeline (componente `<Timeline>`)**: Kp, Dst, IMF Bz empilhados, sincronizados, com bandas coloridas por classe de tempestade. Hover revela valores; click filtra eventos por janela ±48h.
- **Top storms table**: ordenado por |Dst min|, com "ver eventos" → `/map?t0=...&t1=...`.
- **Storm phase panel**: razão de detecção EPB durante main phase vs recovery vs quiet, em barras.
- **Superposed epoch**: linha tempo +/- 24h do Dst min, taxa de detecção por hora.

**No mapa principal**: rodapé com strip Kp/Dst sincronizada com o time slider.

## Figuras paper

- **fig10_storm_vs_quiet.{pdf,png}**: PR curves (com bootstrap IC) por classe de tempestade.
- **fig11_superposed_epoch.{pdf,png}**: taxa de detecção EPB centrada no Dst min, ±48h, com bandas IC95.
- **fig12_storm_event_table.tex**: tabela LaTeX das ~10 maiores tempestades do período + concordância.

## Entrega

Sequência (executada por mim agora, sem confirmação adicional pelo usuário):

1. ✅ docs/plan-phase2-storms-and-external-labels.md (este arquivo).
2. `src/epb_detector/external/space_weather.py` + cache parquet.
3. `src/epb_detector/external/storms.py` (classifier + phase).
4. `src/epb_detector/external/case_studies.yaml` + loader.
5. `src/epb_detector/labels/v2_external.py` + reconcile.
6. Re-execução do pipeline (features → labels v2 → snapshot v1 → train xgb_v0.2.0).
7. Routers `/storms`, `/storms/timeline`, `/storms/superposed-epoch` na FastAPI.
8. Página `/storms` no Next.js + componentes Timeline, StormStrip, SuperposedEpoch.
9. `paper/scripts/make_fig10_storm_vs_quiet.py` + `make_fig11_superposed_epoch.py`.
10. Testes unit + Playwright para tudo acima.
11. Atualizar CLAUDE.md com a nova arquitetura.

## Riscos

- **OMNIWeb 1-min files são grandes** (~50 MB/mês). Mitigar baixando apenas os meses necessários e armazenando só colunas Bz, Vsw, Np, AE.
- **WDC Kyoto Dst format**: arquivo Fortran fixo (`dst<YYMM>.for.request`) — parsing manual.
- **GFZ Kp ASCII** mudou formato em 2018: o módulo precisa lidar com legado e novo.
- **EMBRACE auth** não está disponível agora — Plano A (lista de casos) cobre o gap mas é menos volumoso. Documentado.
- **PR-AUC vai cair** quando avaliada no holdout literature-v1 (esperado e desejável — significa que a métrica é honesta).
