from lib.rdq import Profile
from lib.rdq.svclambda import LambdaClient

from lib.base import initLogging
import lib.lambdas.core.parser as cp
import lib.lambdas.core.analyzer as ca


def make_invocations(profile, functionCallList):
    lambdac = LambdaClient(profile)
    for functionCall in functionCallList:
        functionName = functionCall['functionName']
        event = functionCall['event']
        functionResponse = lambdac.invokeFunctionJson(functionName, event)
        ca.analyzeResponse(functionName, event, functionResponse)


def lambda_handler(event, context):
    initLogging()
    dispatchList = cp.createDispatchList(event)
    if len(dispatchList) == 0: return
    profile = Profile()
    parser = cp.Parser(profile)
    functionCallList = parser.createInvokeList(dispatchList)
    if len(functionCallList) == 0: return
    make_invocations(profile, functionCallList)

