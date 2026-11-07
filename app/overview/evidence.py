"""Allowlisted, tenant-checked evidence and entity drill-downs. Never expose raw payloads."""
from django.db.models import Q
from django.http import Http404

from app import models
from .catalog import ENTITY_DOMAINS, domain_for
from .metrics import snapshot_data


ENTITIES = {
    'order': ('Order', 'business_id', 'order_number'), 'customer': ('Customer', 'business_id', 'display_name'),
    'product': ('Product', 'business_id', 'name'), 'product_variant': ('ProductVariant', 'product__business_id', 'name'),
    'payment': ('Payment', 'business_id', None), 'refund': ('Refund', 'payment__business_id', None),
    'campaign': ('Campaign', 'business_id', 'name'), 'conversation': ('Conversation', 'business_id', 'subject'),
    'shipment': ('Shipment', 'business_id', 'tracking_code'), 'call': ('Call', 'business_id', None),
    'website_session': ('WebsiteSession', 'business_id', None), 'website_visitor': ('WebsiteVisitor', 'business_id', None),
}
KINDS = {'facts': 'BusinessFact', 'snapshots': 'MetricSnapshot', 'relationships': 'BusinessRelationship',
         'nodes': 'GraphNode', 'edges': 'GraphEdge', 'knowledge': 'KnowledgeChunk'}
LINKS = {'business_fact': 'facts', 'metric_snapshot': 'snapshots', 'relationship': 'relationships',
         'business_relationship': 'relationships', 'graph_node': 'nodes', 'graph_edge': 'edges',
         'knowledge_chunk': 'knowledge', 'business_issue': 'issues'}
RELATED = ['business_fact', 'metric_snapshot__metric', 'relationship']
REC_RELATED = ['business_fact', 'business_issue', 'metric_snapshot__metric', 'business_relationship',
               'graph_node', 'graph_edge__source_node', 'graph_edge__target_node', 'graph_edge__business_relationship',
               'knowledge_chunk__knowledge_document__knowledge_source']


class EvidenceProjection:
    def __init__(self, business_id, now):
        self.business_id, self.now = business_id, now
        self._entities = {}

    def href(self, kind, pk):
        prefix = '' if kind in {'issues', 'recommendations'} else 'evidence/'
        return f'/api/businesses/{self.business_id}/overview/{prefix}{kind}/{pk}/'

    def prime_entities(self, references):
        """Batch entity labels by type so list queries do not grow with the page size."""
        grouped = {}
        for kind, pk in references:
            if kind and pk is not None:
                grouped.setdefault(kind.lower(), set()).add(pk)
        for kind, ids in grouped.items():
            spec = ENTITIES.get(kind)
            if not spec:
                continue
            name, scope, label = spec
            model = getattr(models, name)
            fields = ['pk', 'created_at'] + ([label] if label else [])
            fields += [f for f in ('status', 'updated_at') if any(field.name == f for field in model._meta.fields)]
            rows = model.objects.filter(**{scope: self.business_id, 'pk__in': ids, 'created_at__lte': self.now}).values(*fields)
            found = {}
            for row in rows:
                pk = row['pk']
                found[pk] = {'type': kind, 'id': pk, 'domain': ENTITY_DOMAINS.get(kind), 'available': True,
                    'label': row.get(label) if label else f'{kind} #{pk}', 'status': row.get('status'),
                    'updated_at': row.get('updated_at', row['created_at']),
                    'drilldown': f'/api/businesses/{self.business_id}/overview/entities/{kind}/{pk}/'}
            for pk in ids:
                self._entities[(kind, pk)] = found.get(pk, {'type': kind, 'id': pk, 'domain': ENTITY_DOMAINS.get(kind),
                    'available': False, 'label': None, 'drilldown': None})

    def prime_findings(self, rows):
        references = []
        for row in rows:
            references.append((getattr(row, 'subject_entity_type', None), getattr(row, 'subject_entity_id', None)))
            if isinstance(row, models.AiRecommendation) and row.business_issue_id:
                references.append((row.business_issue.subject_entity_type, row.business_issue.subject_entity_id))
            for item in getattr(row, 'monitoring_evidence', []):
                references.append((getattr(item, 'entity_type', None), getattr(item, 'entity_id', None)))
                for field in ('relationship', 'business_relationship'):
                    if getattr(item, field+'_id', None):
                        relation = getattr(item, field)
                        references.extend([(relation.source_entity_type, relation.source_entity_id),
                                           (relation.target_entity_type, relation.target_entity_id)])
                if getattr(item, 'graph_node_id', None):
                    references.append((item.graph_node.entity_type, item.graph_node.entity_id))
                if getattr(item, 'graph_edge_id', None):
                    edge = item.graph_edge
                    references.extend([(edge.source_node.entity_type, edge.source_node.entity_id),
                                       (edge.target_node.entity_type, edge.target_node.entity_id)])
                    if edge.business_relationship_id:
                        relation = edge.business_relationship
                        references.extend([(relation.source_entity_type, relation.source_entity_id),
                                           (relation.target_entity_type, relation.target_entity_id)])
        self.prime_entities(references)

    def entity(self, entity_type, pk):
        if not entity_type or pk is None:
            return None
        entity_type = entity_type.lower()
        key = (entity_type, pk)
        if key in self._entities:
            return self._entities[key]
        data = {'type': entity_type, 'id': pk, 'domain': ENTITY_DOMAINS.get(entity_type),
                'available': False, 'label': None, 'drilldown': None}
        spec = ENTITIES.get(entity_type)
        if spec:
            name, scope, label = spec
            row = getattr(models, name).objects.filter(**{scope: self.business_id, 'pk': pk,
                                                          'created_at__lte': self.now}).first()
            if row:
                data.update(available=True, label=getattr(row, label) if label else f'{entity_type} #{pk}',
                            drilldown=f'/api/businesses/{self.business_id}/overview/entities/{entity_type}/{pk}/',
                            status=getattr(row, 'status', None), updated_at=getattr(row, 'updated_at', row.created_at))
        self._entities[key] = data
        return data

    def owned(self, row):
        if row is None or row.business_id != self.business_id or row.created_at > self.now:
            return False
        if isinstance(row, models.MetricSnapshot):
            return row.metric.business_id == self.business_id and row.calculated_at <= self.now and row.period_end <= self.now
        if isinstance(row, models.BusinessFact):
            return row.status == 'VERIFIED' and row.detected_at <= self.now and self.validity(row)
        if isinstance(row, models.BusinessRelationship):
            return self.validity(row) and all(self.entity(kind, pk)['available']
                for kind, pk in [(row.source_entity_type, row.source_entity_id), (row.target_entity_type, row.target_entity_id)])
        if isinstance(row, models.GraphNode):
            return self.entity(row.entity_type, row.entity_id)['available']
        if isinstance(row, models.GraphEdge):
            return self.owned(row.source_node) and self.owned(row.target_node) and self.validity(row) and (
                not row.business_relationship_id or self.owned(row.business_relationship))
        if isinstance(row, models.KnowledgeChunk):
            document = row.knowledge_document
            return document.business_id == self.business_id and document.knowledge_source.business_id == self.business_id
        return True

    def validity(self, row):
        return (row.valid_from is None or row.valid_from <= self.now) and (row.valid_to is None or row.valid_to > self.now)

    def reference(self, kind, row):
        data = {'kind': kind, 'id': row.pk, 'drilldown': self.href(kind, row.pk)}
        if kind == 'snapshots':
            data.update(snapshot_data(row), metric=row.metric.key, unit=row.metric.unit,
                        category=row.metric.category, domain=domain_for(row.metric))
        elif kind == 'facts':
            data.update(statement=row.statement, confidence=str(row.confidence), detected_at=row.detected_at,
                        rule_key=row.rule_key, status=row.status)
        elif kind == 'relationships':
            data.update(relationship_type=row.relationship_type, source=self.entity(row.source_entity_type, row.source_entity_id),
                        target=self.entity(row.target_entity_type, row.target_entity_id),
                        confidence=str(row.confidence), relationship_source=row.relationship_source, rule_key=row.rule_key)
        elif kind == 'nodes':
            data.update(label=row.label, entity=self.entity(row.entity_type, row.entity_id))
        elif kind == 'edges':
            data.update(relationship_type=row.relationship_type, source_node_id=row.source_node_id,
                        target_node_id=row.target_node_id, business_relationship_id=row.business_relationship_id)
        elif kind == 'knowledge':
            data.update(document_id=row.knowledge_document_id, document_title=row.knowledge_document.title,
                        excerpt=row.content[:800])
        elif kind == 'issues':
            data.update(title=row.title, status=row.status, severity=row.severity)
        return data

    def evidence(self, rows, limit=50):
        output = []
        for row in rows:
            if row.created_at > self.now:
                continue
            references, invalid = [], False
            for field, kind in LINKS.items():
                if (field == 'business_issue' and isinstance(row, models.BusinessIssueEvidence)) or (
                        field == 'business_fact' and isinstance(row, models.BusinessFactEvidence)):
                    continue
                if getattr(row, field+'_id', None) is None:
                    continue
                target = getattr(row, field)
                if not self.owned(target):
                    invalid = True
                    break
                references.append(self.reference(kind, target))
            entity = self.entity(getattr(row, 'entity_type', None), getattr(row, 'entity_id', None))
            if invalid or (entity and not entity['available']) or not (references or entity):
                continue
            output.append({'id': row.pk, 'type': row.evidence_type, 'description': row.description,
                           'weight': str(row.weight) if row.weight is not None else None,
                           'references': references, 'entity': entity})
            if len(output) >= limit:
                break
        return output

    def issue_evidence(self, row):
        rows = getattr(row, 'monitoring_evidence', None)
        if rows is None:
            rows = row.businessissueevidence_set.select_related(*RELATED).order_by('pk')[:101]
        return self.evidence(rows)

    def recommendation_evidence(self, row):
        rows = getattr(row, 'monitoring_evidence', None)
        if rows is None:
            rows = row.airecommendationevidence_set.select_related(*REC_RELATED).order_by('pk')[:101]
        return self.evidence(rows)

    def graph_context(self, entity_type, entity_id):
        if not entity_type or entity_id is None:
            return {'nodes': [], 'edges': []}
        nodes = list(models.GraphNode.objects.filter(business_id=self.business_id,
            entity_type__iexact=entity_type, entity_id=entity_id)[:10])
        ids = [r.pk for r in nodes if self.owned(r)]
        edges = models.GraphEdge.objects.filter(business_id=self.business_id).filter(
            Q(source_node_id__in=ids) | Q(target_node_id__in=ids)).select_related(
                'source_node', 'target_node', 'business_relationship')[:51]
        return {'nodes': [self.reference('nodes', r) for r in nodes if r.pk in ids],
                'edges': [self.reference('edges', r) for r in edges if self.owned(r)][:50]}

    def detail(self, kind, pk):
        name = KINDS.get(kind)
        if not name:
            raise Http404
        query = getattr(models, name).objects.filter(business_id=self.business_id, pk=pk)
        if kind == 'snapshots':
            query = query.select_related('metric')
        elif kind == 'edges':
            query = query.select_related('source_node', 'target_node', 'business_relationship')
        elif kind == 'knowledge':
            query = query.select_related('knowledge_document__knowledge_source')
        row = query.first()
        if not self.owned(row):
            raise Http404
        data = self.reference(kind, row)
        if kind == 'facts':
            data['evidence'] = self.evidence(row.businessfactevidence_set.select_related(
                'metric_snapshot__metric', 'relationship').order_by('pk')[:101])
        return data
