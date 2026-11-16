"""MetaMetrics — a framework-independent Python library for the Meta Marketing API."""

from __future__ import annotations

from metametrics.account.dto import AccountDTO
from metametrics.account.service import AccountService
from metametrics.ad.dto import AdDTO
from metametrics.ad.query import AdQuery
from metametrics.ad.service import AdService
from metametrics.adset.dto import AdSetDTO
from metametrics.adset.query import AdSetQuery
from metametrics.adset.service import AdSetService
from metametrics.auth.service import AuthenticationResult, AuthenticationService
from metametrics.campaign.dto import CampaignDTO
from metametrics.campaign.query import CampaignQuery
from metametrics.campaign.service import CampaignService
from metametrics.client import (
    JsonResponseDecoder,
    MetaClient,
    MetaClientProtocol,
    Request,
    Response,
)
from metametrics.config import ConfigurationValidator, MetaConfig
from metametrics.errors.mapper import MetaErrorMapper
from metametrics.errors.model import MetaError
from metametrics.errors.parser import MetaErrorParser
from metametrics.exceptions import (
    AuthenticationError,
    InvalidConfigurationError,
    InvalidInputError,
    MetaAdsError,
    NetworkError,
    PermissionDeniedError,
    RateLimitError,
    ResourceNotFoundError,
    UnexpectedResponseError,
    UnsupportedMetricError,
)
from metametrics.hierarchy.node import HierarchyNode
from metametrics.hierarchy.result import HierarchyResult
from metametrics.hierarchy.service import HierarchyService
from metametrics.historical.delivery import (
    DeliveryAssessment,
    DeliveryDiscovery,
    DeliveryDiscoveryProtocol,
    DeliveryEvidence,
    DeliveryStatus,
)
from metametrics.historical.level import HistoricalLevel
from metametrics.historical.query import HistoricalQuery
from metametrics.historical.response import HistoricalResponse
from metametrics.historical.result import HistoricalResult
from metametrics.historical.service import HistoricalService
from metametrics.insights.aggregation import MetricAggregator
from metametrics.insights.aggregation_result import MetricAggregationResult
from metametrics.insights.date_range.preset import DatePreset
from metametrics.insights.date_range.range import DateRange
from metametrics.insights.date_range.timezone import AccountTimezone
from metametrics.insights.dto import InsightsDTO
from metametrics.insights.filter_fields import InsightsFilterField
from metametrics.insights.level import InsightsLevel
from metametrics.insights.metrics.calculator import MetricCalculator
from metametrics.insights.metrics.definition import MetricDefinition
from metametrics.insights.metrics.metric import Metric
from metametrics.insights.metrics.purchase_actions import PurchaseActionMapping
from metametrics.insights.metrics.registry import MetricRegistry
from metametrics.insights.metrics.types import MetricAggregation, MetricType, MetricUnit
from metametrics.insights.query import InsightsQuery
from metametrics.insights.raw_data import InsightsRawData
from metametrics.insights.response import InsightsResponse
from metametrics.insights.service import InsightsService
from metametrics.meta_ads import MetaAds
from metametrics.pagination.paginator import Paginator
from metametrics.pagination.result import PaginationResult
from metametrics.query.builder import QueryBuilder
from metametrics.query.fields import Fields
from metametrics.query.filters import Filter, FilterOperator
from metametrics.tracking.identifiers import TrackingIdentifiers
from metametrics.tracking.parser import TrackingUrlParser

__all__ = [
    "AccountDTO",
    "AccountService",
    "AccountTimezone",
    "AdDTO",
    "AdQuery",
    "AdService",
    "AdSetDTO",
    "AdSetQuery",
    "AdSetService",
    "AuthenticationError",
    "AuthenticationResult",
    "AuthenticationService",
    "CampaignDTO",
    "CampaignQuery",
    "CampaignService",
    "ConfigurationValidator",
    "DatePreset",
    "DateRange",
    "DeliveryAssessment",
    "DeliveryDiscovery",
    "DeliveryDiscoveryProtocol",
    "DeliveryEvidence",
    "DeliveryStatus",
    "Fields",
    "Filter",
    "FilterOperator",
    "HierarchyNode",
    "HierarchyResult",
    "HierarchyService",
    "HistoricalLevel",
    "HistoricalQuery",
    "HistoricalResponse",
    "HistoricalResult",
    "HistoricalService",
    "InsightsDTO",
    "InsightsFilterField",
    "InsightsLevel",
    "InsightsQuery",
    "InsightsRawData",
    "InsightsResponse",
    "InsightsService",
    "InvalidConfigurationError",
    "InvalidInputError",
    "JsonResponseDecoder",
    "MetaAds",
    "MetaAdsError",
    "MetaClient",
    "MetaClientProtocol",
    "MetaConfig",
    "MetaError",
    "MetaErrorMapper",
    "MetaErrorParser",
    "Metric",
    "MetricAggregation",
    "MetricAggregationResult",
    "MetricAggregator",
    "MetricCalculator",
    "MetricDefinition",
    "MetricRegistry",
    "MetricType",
    "MetricUnit",
    "NetworkError",
    "PaginationResult",
    "Paginator",
    "PermissionDeniedError",
    "PurchaseActionMapping",
    "QueryBuilder",
    "RateLimitError",
    "Request",
    "ResourceNotFoundError",
    "Response",
    "TrackingIdentifiers",
    "TrackingUrlParser",
    "UnexpectedResponseError",
    "UnsupportedMetricError",
]

__version__ = "1.0.0"
