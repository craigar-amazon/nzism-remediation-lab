import botocore

from lib.base import Tags
from lib.rdq import RdqError
from lib.rdq.base import ServiceUtils

def _create_dimlist(dimensionMap: dict):
    dimlist = []
    for key in dimensionMap:
        item = {
            'Name': key,
            'Value': dimensionMap[key]
        }
        dimlist.append(item)
    return dimlist

class CwmClient:
    def __init__(self, profile, maxAttempts=10):
        service = 'cloudwatch'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service, maxAttempts)

    def put_metric_data(self, namespace, metricDataList :list):
        op = 'put_metric_data'
        try:
            self._client.put_metric_data(
                Namespace=namespace,
                MetricData=metricDataList
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'Namespace', namespace))

    def put_metric_datum(self, namespace, metric :dict):
        self.put_metric_data(namespace, [metric])

    def putCount(self, namespace, metricName, dimensionMap :dict, value=1.0):
        metric = {}
        metric['MetricName'] = metricName
        metric['Dimensions'] = _create_dimlist(dimensionMap)
        metric['Value'] = value
        metric['Unit'] = 'Count'
        self.put_metric_datum(namespace, metric)

