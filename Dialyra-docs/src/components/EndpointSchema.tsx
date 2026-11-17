import { Fragment } from 'react'
import type { ApiVersion } from '../config/docsConfig'
import { getEndpointSchemaBlocks } from '../config/schemaExtract'
import type { Endpoint } from '../config/docsPages'

type EndpointSchemaProps = {
  endpoint: Endpoint
  version: ApiVersion
}

function InlineMarkdown({ text }: { text: string }) {
  const parts = text.split(/(`[^`]+`)/g)

  return (
    <>
      {parts.map((part, index) =>
        part.startsWith('`') && part.endsWith('`') ? (
          <code className="inline-code" key={`${part}-${index}`}>
            {part.slice(1, -1)}
          </code>
        ) : (
          <Fragment key={`${part}-${index}`}>{part}</Fragment>
        ),
      )}
    </>
  )
}

export function EndpointSchema({ endpoint, version }: EndpointSchemaProps) {
  const blocks = getEndpointSchemaBlocks(version, endpoint)

  if (blocks.length === 0 && !endpoint.details) {
    return null
  }

  return (
    <details className="endpoint-schema">
      <summary>Request and response schema</summary>
      <div className="schema-blocks">
        {endpoint.details?.map((detail) => (
          <section className="detail-panel" key={detail.title}>
            <h3>{detail.title}</h3>
            {detail.description ? <p>{detail.description}</p> : null}
            {detail.items ? (
              <ul>
                {detail.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
            {detail.code ? (
              <pre>
                <code>{detail.code}</code>
              </pre>
            ) : null}
          </section>
        ))}
        {blocks.map((block, index) => {
          if (block.type === 'heading') {
            return <h3 key={`${block.text}-${index}`}>{block.text}</h3>
          }

          if (block.type === 'list') {
            return (
              <ul key={`list-${index}`}>
                {block.items.map((item) => (
                  <li key={item}>
                    <InlineMarkdown text={item} />
                  </li>
                ))}
              </ul>
            )
          }

          if (block.type === 'code') {
            return (
              <pre key={`code-${index}`}>
                <code>{block.code}</code>
              </pre>
            )
          }

          return (
            <p key={`${block.text}-${index}`}>
              <InlineMarkdown text={block.text} />
            </p>
          )
        })}
      </div>
    </details>
  )
}
