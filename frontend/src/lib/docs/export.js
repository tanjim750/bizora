/**
 * Bizora Docs Module — Export Utilities (Markdown download, PDF Print, Share Link)
 */

export function generateMarkdownExport(pitchSections, technicalSections, teamMembers, liveStats) {
  const dateStr = new Date().toISOString().split('T')[0]
  let md = `# Bizora — Autonomous Enterprise Business Brain\n`
  md += `*Live YC-Style Pitch Deck & Deep Technical Whitepaper*\n\n`
  md += `**Exported on:** ${dateStr}  \n`
  md += `**Authoritative System Status:** ${liveStats?.systemStatus || 'OPERATIONAL'}  \n`
  md += `**Platform GMV Processed:** ${liveStats?.grossMerchandiseValue || 'BDT 48,290,400.00'}  \n\n`
  md += `---\n\n`

  // Table of Contents
  md += `## Table of Contents\n\n`
  md += `### Part 1: Y Combinator-Style Pitch Deck\n`
  pitchSections.forEach((s) => {
    md += `- [${s.title}](#${s.id})\n`
  })
  md += `\n### Part 2: Deep Technical Whitepaper\n`
  technicalSections.forEach((s) => {
    md += `- [${s.title}](#${s.id})\n`
  })
  md += `\n---\n\n`

  // Part 1: Pitch Deck
  md += `## Part 1: YC-Style Pitch Deck\n\n`
  pitchSections.forEach((sec) => {
    md += `### <a id="${sec.id}"></a>${sec.title}\n`
    if (sec.tagline) md += `*${sec.tagline}*\n\n`
    if (sec.summary) md += `${sec.summary}\n\n`

    if (sec.points) {
      sec.points.forEach((pt) => {
        md += `#### ${pt.title}\n${pt.detail}\n\n`
      })
    }

    if (sec.modules) {
      md += `| Workspace | Capabilities | Class |\n|---|---|---|\n`
      sec.modules.forEach((m) => {
        md += `| **${m.name}** | ${m.description} | \`${m.badge}\` |\n`
      })
      md += `\n`
    }

    if (sec.metrics) {
      md += `| Metric | Figure | Description |\n|---|---|---|\n`
      sec.metrics.forEach((m) => {
        md += `| **${m.label}** | \`${m.value}\` | ${m.subtitle} |\n`
      })
      md += `\n`
    }

    if (sec.tiers) {
      sec.tiers.forEach((t) => {
        md += `#### ${t.name} (${t.price})\n`
        md += `${t.subtitle}\n\n`
        t.features.forEach((f) => {
          md += `- ${f}\n`
        })
        md += `\n`
      })
    }

    if (sec.matrix) {
      md += `| Capability | Bizora | Shopify | SAP / Odoo | Single-Point Tools |\n|---|---|---|---|---|\n`
      sec.matrix.forEach((r) => {
        md += `| **${r.feature}** | **${r.bizora}** | ${r.shopify} | ${r.sapOdoo} | ${r.pointTools} |\n`
      })
      md += `\n`
    }

    if (sec.moats) {
      sec.moats.forEach((m) => {
        md += `#### ${m.title}\n${m.description}\n\n`
      })
    }

    if (sec.pillars) {
      sec.pillars.forEach((p) => {
        md += `#### ${p.phase}\n${p.description}\n\n`
      })
    }

    if (sec.id === 'team') {
      md += `#### Core Architecture Team\n\n`
      teamMembers.forEach((m) => {
        md += `- **${m.name}** (${m.role}) — \`${m.email}\`\n  ${m.bio}\n  *Focus:* ${m.focusAreas?.join(', ')}\n\n`
      })
    }
  })

  // Part 2: Technical Whitepaper
  md += `\n---\n\n## Part 2: Deep Technical Whitepaper\n\n`
  technicalSections.forEach((sec) => {
    md += `### <a id="${sec.id}"></a>${sec.title}\n\n`
    if (sec.summary) md += `${sec.summary}\n\n`

    if (sec.layers) {
      sec.layers.forEach((l) => {
        md += `#### Layer: ${l.layer}\n`
        md += `- **Stack:** ${l.technologies}\n`
        md += `- **Architectural Rationale:** ${l.rationale}\n\n`
      })
    }

    if (sec.endpoints) {
      md += `| Method | Endpoint | Auth | Role | Description |\n|---|---|---|---|---|\n`
      sec.endpoints.forEach((ep) => {
        md += `| \`${ep.method}\` | \`${ep.path}\` | ${ep.auth} | \`${ep.role}\` | ${ep.description} |\n`
      })
      md += `\n`
    }

    if (sec.points) {
      sec.points.forEach((p) => {
        md += `#### ${p.title}\n${p.detail}\n\n`
      })
    }

    if (sec.milestones) {
      sec.milestones.forEach((m) => {
        md += `#### [${m.status}] ${m.quarter}: ${m.title}\n`
        m.deliverables.forEach((d) => {
          md += `- ${d}\n`
        })
        md += `\n`
      })
    }

    if (sec.releases) {
      sec.releases.forEach((r) => {
        md += `#### Release ${r.version} (${r.date})\n`
        r.highlights.forEach((h) => {
          md += `- ${h}\n`
        })
        md += `\n`
      })
    }
  })

  return md
}

export function downloadMarkdownFile(filename, content) {
  if (typeof window === 'undefined') return
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || 'bizora-docs-whitepaper.md'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export function triggerPrintPdf() {
  if (typeof window === 'undefined') return
  window.print()
}

export async function copyShareableLink(anchorId) {
  if (typeof window === 'undefined') return false
  try {
    const url = new URL(window.location.href)
    if (anchorId) url.hash = anchorId
    await navigator.clipboard.writeText(url.toString())
    return true
  } catch {
    return false
  }
}
