# ByteCrawl — Perfil de diseño

Sistema visual de la landing, `/methods`, `/try` y `/docs`. Toda página nueva debe seguir esto.
Inspiración: Vercel / chat-sdk.dev (light theme, limpio, técnico).

## Principios

1. **Neutral por defecto, nunca verde.** La marca es blanco/negro/gris. El acento es negro (`#09090b`), no un color.
2. **Un solo color de realce: ámbar.** Se usa con moderación para señales "en vivo" o de atención: pill de tiempo, badge de estrategia, callout de "por qué". Nada más lleva color.
3. **Mono para lo técnico.** URLs, comandos, conteos, tokens, nombres de archivo y badges van en JetBrains Mono.
4. **Bordes suaves, sin sombras fuertes.** Tarjetas con borde de 1px; sombra solo sutil en hover.
5. **Números solo si son reproducibles.** Ninguna métrica inventada en la UI (ver historial: se quitaron `∞` y `122×`).

## Color (tokens CSS `:root`)

| Token | Valor | Uso |
|---|---|---|
| `--bg` / `--panel` | `#ffffff` | fondo y paneles |
| `--panel-2` | `#f7f7f8` | fondos secundarios (badges, code inline, tracks) |
| `--border` | `#e6e6e9` | bordes por defecto |
| `--border-2` | `#d4d4d8` | bordes en hover / inputs |
| `--text` | `#09090b` | texto principal |
| `--muted` | `#6b7280` | texto secundario |
| `--muted-2` | `#3f3f46` | texto de datos en tablas |
| `--accent` | `#09090b` | acento (negro neutro, NO verde) |
| `--code-bg` | `#f6f8fa` | fondo de bloques de código |

**Realce ámbar** (único color permitido, uso puntual): texto `#b45309` / `#713f12`, fondo `#fffbeb`, borde `#fde68a`.

**Estados:** error `#dc2626` · en ejecución (`run`) ámbar `#b45309` · ok = `--accent`.

**Sintaxis de código:** keyword `#cf222e` · string `#0a3069` · función `#8250df` · comentario `#6e7781` · número/const `#0550ae`.

## Tipografía

- **UI:** Inter. Pesos 400/500/600/700/800. H1 44–56px (-1.5 a -2px tracking, weight 800), H2 ~20–38px, body 14–17px, micro 12–13px.
- **Mono:** JetBrains Mono. Para todo lo técnico.

## Forma y espacio

- **Radio:** 6px (badges/code inline) · 8–10px (botones, inputs, pills, callouts) · 12–14px (tarjetas, contenedores).
- **Ancho de contenido:** `.wrap` máx 1100px, padding lateral 24px.
- **Gap de grid:** 18–20px.

## Componentes

- **Nav:** sticky, fondo `rgba(255,255,255,.75)` + `backdrop-filter: blur(12px)`, borde inferior. Logo en 800 con punto `--accent`. Links `--muted`; activo `--text` weight 600.
- **Botón primario (`.btn`):** fondo `--text`, texto blanco, radio 9px, weight 600. Hover `#27272a`.
- **Tarjeta:** fondo panel, borde 1px, radio 14px, padding ~22px. Hover: borde `--border-2` + sombra `0 4px 20px rgba(0,0,0,.04)`.
- **Badge/pill técnico:** mono 11–13px, fondo `--panel-2`, borde 1px, radio 6px.
- **Pill de tiempo / estrategia:** ámbar (fondo `#fef3c7`/`#fffbeb`, borde `#fde68a`), mono, weight 700.
- **Ventana de código:** barra con 3 puntos (rojo `#ff5f56`, ámbar `#ffbd2e`, verde `#27c93f` — decorativos de macOS, única excepción al "no verde") + nombre de archivo en mono.
- **Callout "por qué":** caja ámbar; título en `<b>` arriba, texto debajo.
- **Bloque de resultado (`pre`):** fondo `--code-bg`, borde, radio 10px, mono 11px, `white-space: pre-wrap`, scroll a 200px.
- **Stat:** número grande (34px, weight 800) + label `--muted`.

## Toggle (humans/agents)

Segmentos de texto, sin caja: inactivo `--muted` weight 500, activo `--text` weight 600. Cambia contenido al click.

## Reglas al crear UI nueva

1. Copia los tokens `:root` y las fuentes tal cual.
2. Resultados (datos, markdown, tablas) usan los estilos `pre` / `table` / `.count` existentes — mismo look en todas las páginas.
3. Si necesitas atención visual, usa ámbar, no inventes colores.
4. El nav siempre lleva: `Docs · Methods · Try · GitHub`.
