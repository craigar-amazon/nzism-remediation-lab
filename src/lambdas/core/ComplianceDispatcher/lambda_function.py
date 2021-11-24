from lib.rdq import Profile
from lib.rdq.svclambda import LambdaClient

from lib.core.parser import createDispatchList, createInvokeList
from lib.core.analyzer import analyzeResponse


def make_invocations(profile, functionCallList):
    lambdac = LambdaClient(profile)
    for functionCall in functionCallList:
        functionName = functionCall['functionName']
        event = functionCall['event']
        functionResponse = lambdac.invokeFunctionJson(functionName, event)
        analyzeResponse(functionName, event, functionResponse)


def lambda_handler(event, context):
    dispatchList = createDispatchList(event)
    if len(dispatchList) == 0: return
    profile = Profile()
    functionCallList = createInvokeList(profile, dispatchList)
    if len(functionCallList) == 0: return
    make_invocations(profile, functionCallList)

