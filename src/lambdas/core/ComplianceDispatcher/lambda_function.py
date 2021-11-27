from lib.rdq import Profile
from lib.rdq.svclambda import LambdaClient

from lib.base import initLogging
import lib.core.parser as parser
import lib.core.analyzer as analyzer


def make_invocations(profile, functionCallList):
    lambdac = LambdaClient(profile)
    for functionCall in functionCallList:
        functionName = functionCall['functionName']
        event = functionCall['event']
        functionResponse = lambdac.invokeFunctionJson(functionName, event)
        analyzer.analyzeResponse(functionName, event, functionResponse)


def lambda_handler(event, context):
    initLogging()
    dispatchList = parser.createDispatchList(event)
    if len(dispatchList) == 0: return
    profile = Profile()
    functionCallList = parser.createInvokeList(profile, dispatchList)
    if len(functionCallList) == 0: return
    make_invocations(profile, functionCallList)

