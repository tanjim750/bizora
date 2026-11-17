import v2SchemaMarkdown from '../../docs/v2/api_request_response_schema_v2.md?raw'
import v3SchemaMarkdown from '../../docs/v3/api_request_response_schema_v3.md?raw'
import type { ApiVersion } from './docsConfig'
import type { Endpoint } from './docsPages'

type MarkdownBlock =
  | { type: 'heading'; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'list'; items: string[] }
  | { type: 'code'; language: string; code: string }

type EndpointSection = {
  method: Endpoint['method']
  path: string
  blocks: MarkdownBlock[]
}

const schemaByVersion: Partial<Record<ApiVersion, string>> = {
  v2: v2SchemaMarkdown,
  v3: v3SchemaMarkdown,
}

function normalizeEndpointPath(path: string) {
  return path.replace(/`/g, '').split('?')[0].trim()
}

function rewriteApiPrefix(block: MarkdownBlock): MarkdownBlock {
  if (block.type === 'list') {
    return {
      ...block,
      items: block.items.map((item) => item.replaceAll('/api/v2', '/api/v3')),
    }
  }

  if (block.type === 'code' || block.type === 'heading' || block.type === 'paragraph') {
    return {
      ...block,
      [block.type === 'code' ? 'code' : 'text']: (block.type === 'code' ? block.code : block.text).replaceAll(
        '/api/v2',
        '/api/v3',
      ),
    } as MarkdownBlock
  }

  return block
}

function extractEndpointSections(markdown: string): EndpointSection[] {
  const lines = markdown.split('\n')
  const sections: EndpointSection[] = []

  for (let index = 0; index < lines.length; index += 1) {
    const headingMatch = lines[index].match(/^###\s+`(GET|POST|PUT|DELETE)\s+([^`]+)`/)
    const titleMatch = lines[index].match(/^###\s+(.+)/)
    const nextLineMatch = lines[index + 2]?.match(/^`(GET|POST|PUT|DELETE)\s+([^`]+)`/)
    const endpointMatch = headingMatch ?? nextLineMatch

    if (!endpointMatch || !titleMatch) continue

    const [, method, rawPath] = endpointMatch
    const start = headingMatch ? index + 1 : index + 3
    let end = start

    while (end < lines.length && !lines[end].startsWith('### ') && !lines[end].startsWith('## ')) {
      end += 1
    }

    const sectionLines = lines
      .slice(start, end)
      .filter((line) => !line.match(/^`(GET|POST|PUT|DELETE)\s+([^`]+)`/))

    sections.push({
      method: method as Endpoint['method'],
      path: normalizeEndpointPath(rawPath),
      blocks: parseMarkdownBlocks(sectionLines.join('\n')),
    })
  }

  return sections
}

function parseMarkdownBlocks(markdown: string): MarkdownBlock[] {
  const lines = markdown.split('\n')
  const blocks: MarkdownBlock[] = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index].trim()

    if (!line || line === '---') {
      index += 1
      continue
    }

    if (line.startsWith('```')) {
      const language = line.replace('```', '').trim()
      const codeLines: string[] = []
      index += 1

      while (index < lines.length && !lines[index].startsWith('```')) {
        codeLines.push(lines[index])
        index += 1
      }

      blocks.push({ type: 'code', language, code: codeLines.join('\n') })
      index += 1
      continue
    }

    if (line.startsWith('#### ')) {
      blocks.push({ type: 'heading', text: line.replace(/^####\s+/, '') })
      index += 1
      continue
    }

    if (line.startsWith('- ')) {
      const items: string[] = []

      while (index < lines.length && lines[index].trim().startsWith('- ')) {
        items.push(lines[index].trim().replace(/^-\s+/, ''))
        index += 1
      }

      blocks.push({ type: 'list', items })
      continue
    }

    const paragraphLines = [line]
    index += 1

    while (
      index < lines.length &&
      lines[index].trim() &&
      !lines[index].trim().startsWith('- ') &&
      !lines[index].trim().startsWith('```') &&
      !lines[index].trim().startsWith('#### ')
    ) {
      paragraphLines.push(lines[index].trim())
      index += 1
    }

    blocks.push({ type: 'paragraph', text: paragraphLines.join(' ') })
  }

  return blocks
}

const endpointSectionsByVersion = Object.fromEntries(
  Object.entries(schemaByVersion).map(([version, markdown]) => [
    version,
    extractEndpointSections(markdown ?? ''),
  ]),
) as Partial<Record<ApiVersion, EndpointSection[]>>

export function getEndpointSchemaBlocks(version: ApiVersion, endpoint: Endpoint) {
  const normalizedPath = normalizeEndpointPath(endpoint.path)
  const exactBlocks = endpointSectionsByVersion[version]?.find(
    (section) => section.method === endpoint.method && section.path === normalizedPath,
  )?.blocks

  if (exactBlocks) return exactBlocks

  if (version === 'v3' && normalizedPath.startsWith('/api/v3')) {
    const fallbackPath = normalizedPath.replace('/api/v3', '/api/v2')
    const fallbackBlocks = endpointSectionsByVersion.v2?.find(
      (section) => section.method === endpoint.method && section.path === fallbackPath,
    )?.blocks

    return fallbackBlocks?.map(rewriteApiPrefix) ?? []
  }

  return []
}
