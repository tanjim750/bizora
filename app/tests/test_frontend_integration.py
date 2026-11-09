"""Contracts exercised by the separate Next.js operations client."""

from app import models as m
from app.test_domains import DomainFixture
from django.utils import timezone


class FrontendIntegrationTests(DomainFixture):
    def test_campaign_platform_filter_matches_frontend_control(self):
        m.Campaign.objects.create(business=self.business, name='Meta campaign', platform='META')
        m.Campaign.objects.create(business=self.business, name='Google campaign', platform='GOOGLE')

        response = self.client.get(self.url('campaigns/?platform=META'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['platform'], 'META')

    def test_proposal_review_payload_is_scoped_and_does_not_execute(self):
        recommendation = m.AiRecommendation.objects.create(
            business=self.business,
            recommendation_type='TEST',
            title='Review only',
            description='No provider call',
            generated_at=timezone.now(),
        )
        action = m.AiAction.objects.create(
            business=self.business, ai_recommendation=recommendation, action_type='TEST',
        )
        path = self.url(f'actions/{action.pk}/review/')
        self.client.force_authenticate(self.operator)
        self.assertEqual(self.client.post(path, {
            'action_id': action.pk, 'decision': 'REJECTED', 'reason': 'Insufficient evidence',
        }, format='json').status_code, 403)
        self.client.force_authenticate(self.manager)
        response = self.client.post(path, {
            'action_id': action.pk, 'decision': 'REJECTED', 'reason': 'Insufficient evidence',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['action']['status'], 'REJECTED')
        self.assertEqual(response.data['execution']['status'], 'UNAVAILABLE')
        action.refresh_from_db()
        self.assertIsNone(action.executed_at)
